"""Normalize extracted study material and split it into source-aware chunks."""

import hashlib
import json
import re
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.document_processing import ExtractedPage


class ExtractedContent(BaseModel):
    """Common validated input for text, OCR/vision descriptions, and transcripts.

    Location fields are optional and are populated only when the extractor has
    reliable source information. Video timestamps are seconds on the original
    media timeline. ``extraction_warnings`` and ``is_incomplete`` describe the
    extraction itself and are copied to every resulting chunk.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    source_filename: str | None = None
    source_type: str | None = None
    document_id: str | None = None
    source_id: str | None = None
    course_id: str | None = None
    material_id: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    slide_number: int | None = Field(default=None, ge=1)
    timestamp_start_seconds: float | None = Field(default=None, ge=0)
    timestamp_end_seconds: float | None = Field(default=None, ge=0)
    segment_id: str | None = None
    heading: str | None = None
    topic: str | None = None
    content_kind: str = "text"
    extraction_warnings: list[str] = Field(default_factory=list)
    is_incomplete: bool = False

    @model_validator(mode="after")
    def validate_location(self) -> "ExtractedContent":
        """Ensure supplied location metadata is internally consistent."""
        if (
            self.timestamp_start_seconds is not None
            and self.timestamp_end_seconds is not None
            and self.timestamp_end_seconds < self.timestamp_start_seconds
        ):
            raise ValueError("timestamp_end_seconds must not precede the start timestamp")
        return self


# Keep the former public type name for existing PDF, PPT, and video consumers.
SourceSegment = ExtractedContent


class DocumentChunk(BaseModel):
    """Normalized, validated chunk model shared by document ingestion formats."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1)
    document_id: str | None = None
    source_filename: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    course_id: str | None = None
    material_id: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    slide_number: int | None = Field(default=None, ge=1)
    timestamp_start_seconds: float | None = Field(default=None, ge=0)
    timestamp_end_seconds: float | None = Field(default=None, ge=0)
    segment_id: str | None = None
    content_kind: str = "text"
    extraction_warnings: list[str] = Field(default_factory=list)
    is_incomplete: bool = False
    chunk_index: int = Field(ge=0)
    chunk_id: str = Field(min_length=1)
    segment_index: int = Field(default=0, ge=0)
    start_char: int = Field(default=0, ge=0)
    end_char: int = Field(default=0, ge=0)
    heading: str | None = None
    topic: str | None = None

    @model_validator(mode="after")
    def validate_source_location(self) -> "DocumentChunk":
        """Require offsets and timestamps to be ordered."""
        if self.end_char < self.start_char:
            raise ValueError("end_char must be greater than or equal to start_char")
        if (
            self.timestamp_start_seconds is not None
            and self.timestamp_end_seconds is not None
            and self.timestamp_end_seconds < self.timestamp_start_seconds
        ):
            raise ValueError("timestamp_end_seconds must not precede the start timestamp")
        return self


# Backward-compatible name used by retrieval, RAG, and citation modules.
TextChunk = DocumentChunk

_PARAGRAPH_BOUNDARY = re.compile(r"\n\s*\n+")
_SENTENCE_BOUNDARY = re.compile(r"[.!?][\"')\]\u2019\u201d]*\s+")
_WHITESPACE_BOUNDARY = re.compile(r"\s+")


class TextChunker:
    """Split extracted content while retaining source metadata and context."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 150) -> None:
        """Configure maximum characters and target overlap per segment."""
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    @classmethod
    def from_settings(cls, settings: Any | None = None) -> "TextChunker":
        """Build a chunker from application settings, loading them when omitted."""
        if settings is None:
            from app.core.config import get_settings

            settings = get_settings()
        return cls(settings.chunk_size_chars, settings.chunk_overlap_chars)

    def chunk(
        self,
        segments: Iterable[Any],
        document_id: str | None = None,
        *,
        course_id: str | None = None,
        material_id: str | None = None,
    ) -> list[DocumentChunk]:
        """Normalize and chunk content from supported extractors.

        Paragraph and sentence boundaries are preferred when they fit within
        the configured maximum. Whitespace boundaries are the fallback; a
        hard character boundary is used only for a single oversized token or
        sentence. Overlap is a target and can vary slightly to keep boundaries
        readable. Whitespace-only segments never produce chunks.
        """
        chunks: list[DocumentChunk] = []
        next_chunk_index = 0
        for segment_index, raw_segment in enumerate(segments):
            segment = self._normalize_segment(raw_segment, document_id, course_id, material_id)
            original = segment.text
            left_trim = len(original) - len(original.lstrip())
            text = original.strip()
            if not text:
                continue

            start = 0
            while start < len(text):
                hard_end = min(start + self.chunk_size, len(text))
                end = self._select_end(text, start, hard_end)
                raw_chunk = text[start:end]
                leading_trim = len(raw_chunk) - len(raw_chunk.lstrip())
                chunk_text = raw_chunk.strip()
                if chunk_text:
                    source_start = left_trim + start + leading_trim
                    source_end = source_start + len(chunk_text)
                    chunks.append(
                        DocumentChunk(
                            text=chunk_text,
                            document_id=segment.document_id,
                            source_filename=segment.source_filename,
                            source_type=segment.source_type,
                            source_id=segment.source_id,
                            course_id=segment.course_id,
                            material_id=segment.material_id,
                            page_number=segment.page_number,
                            slide_number=segment.slide_number,
                            timestamp_start_seconds=segment.timestamp_start_seconds,
                            timestamp_end_seconds=segment.timestamp_end_seconds,
                            segment_id=segment.segment_id,
                            content_kind=segment.content_kind,
                            extraction_warnings=list(segment.extraction_warnings),
                            is_incomplete=segment.is_incomplete,
                            chunk_index=next_chunk_index,
                            chunk_id=self._stable_chunk_id(
                                segment, segment_index, source_start, source_end, chunk_text
                            ),
                            segment_index=segment_index,
                            start_char=source_start,
                            end_char=source_end,
                            heading=segment.heading,
                            topic=segment.topic,
                        )
                    )
                    next_chunk_index += 1
                if end >= len(text):
                    break
                next_start = self._select_next_start(text, start, end)
                start = max(start + 1, next_start)
        return chunks

    def _select_end(self, text: str, start: int, hard_end: int) -> int:
        """Choose the best readable boundary before the maximum chunk size."""
        if hard_end == len(text):
            return hard_end
        minimum = start + max(1, int((hard_end - start) * 0.45))
        for pattern in (_PARAGRAPH_BOUNDARY, _SENTENCE_BOUNDARY, _WHITESPACE_BOUNDARY):
            matches = [m.end() for m in pattern.finditer(text, start, hard_end + 1)]
            eligible = [point for point in matches if minimum <= point <= hard_end]
            if eligible:
                return max(eligible)
        return hard_end

    def _select_next_start(self, text: str, start: int, end: int) -> int:
        """Choose an overlap start near the target, preferring readable edges."""
        target = max(start + 1, end - self.overlap)
        if self.overlap == 0:
            return end
        tolerance = max(1, self.overlap // 2)
        lower = max(start + 1, target - tolerance)
        upper = min(end - 1, target + tolerance)
        for pattern in (_PARAGRAPH_BOUNDARY, _SENTENCE_BOUNDARY, _WHITESPACE_BOUNDARY):
            points = [m.end() for m in pattern.finditer(text, lower, upper + 1)]
            if points:
                return min(points, key=lambda point: abs(point - target))
        return target

    @staticmethod
    def _normalize_segment(
        raw: Any,
        document_id: str | None,
        course_id: str | None,
        material_id: str | None,
    ) -> ExtractedContent:
        """Adapt current PDF, slide, transcript, and generic OCR result objects."""
        if isinstance(raw, ExtractedPage):
            warnings = list(getattr(raw, "extraction_warnings", []) or [])
            requires_ocr = bool(getattr(raw, "requires_ocr", False))
            if requires_ocr:
                warnings.append("Page has no extractable text and requires OCR.")
            return ExtractedContent(
                text=raw.text,
                source_filename=raw.source_filename,
                source_type=raw.source_type,
                document_id=document_id,
                course_id=course_id,
                material_id=material_id,
                page_number=raw.page_number,
                content_kind="text",
                extraction_warnings=warnings,
                is_incomplete=requires_ocr,
            )

        if isinstance(raw, ExtractedContent):
            values = raw.model_dump()
        else:
            # Structural adapter keeps the chunker independent from processor
            # modules and their import graph. It supports ExtractedSlide and
            # TranscriptionSegment objects as well as OCR/vision adapters.
            values = {
                "text": getattr(raw, "text", ""),
                "source_filename": getattr(raw, "source_filename", None),
                "source_type": getattr(raw, "source_type", None),
                "document_id": getattr(raw, "document_id", None),
                "source_id": getattr(raw, "source_id", None),
                "course_id": getattr(raw, "course_id", None),
                "material_id": getattr(raw, "material_id", None),
                "page_number": getattr(raw, "page_number", None),
                "slide_number": getattr(raw, "slide_number", None),
                "timestamp_start_seconds": getattr(
                    raw, "timestamp_start_seconds", getattr(raw, "start_seconds", None)
                ),
                "timestamp_end_seconds": getattr(
                    raw, "timestamp_end_seconds", getattr(raw, "end_seconds", None)
                ),
                "segment_id": getattr(raw, "segment_id", None),
                "heading": getattr(raw, "heading", getattr(raw, "title", None)),
                "topic": getattr(raw, "topic", None),
                "content_kind": getattr(raw, "content_kind", "text"),
                "extraction_warnings": getattr(raw, "extraction_warnings", []),
                "is_incomplete": getattr(raw, "is_incomplete", False),
            }
            status = getattr(raw, "status", None)
            if status in {"no_text", "ocr_required"} and not values["extraction_warnings"]:
                values["extraction_warnings"] = [f"Source extraction status: {status}."]
                values["is_incomplete"] = status == "ocr_required"
            if getattr(raw, "image_count", 0):
                image_warning = "Slide contains image assets that were not analyzed by OCR or vision."
                if image_warning not in values["extraction_warnings"]:
                    values["extraction_warnings"] = [*values["extraction_warnings"], image_warning]
                values["is_incomplete"] = True

        for name, supplied in (
            ("document_id", document_id),
            ("course_id", course_id),
            ("material_id", material_id),
        ):
            if supplied is not None and values.get(name) is None:
                values[name] = supplied
        return ExtractedContent.model_validate(values)

    @staticmethod
    def _stable_chunk_id(
        segment: ExtractedContent,
        segment_index: int,
        start_char: int,
        end_char: int,
        text: str,
    ) -> str:
        """Create a stable SHA-256 ID from source identity, location, and text."""
        payload = {
            "document_id": segment.document_id,
            "source_id": segment.source_id,
            "course_id": segment.course_id,
            "material_id": segment.material_id,
            "source_filename": segment.source_filename,
            "source_type": segment.source_type,
            "segment_id": segment.segment_id,
            "segment_index": None if segment.segment_id is not None else segment_index,
            "page_number": segment.page_number,
            "slide_number": segment.slide_number,
            "timestamp_start_seconds": segment.timestamp_start_seconds,
            "timestamp_end_seconds": segment.timestamp_end_seconds,
            "start_char": start_char,
            "end_char": end_char,
            "text": text,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return "chunk_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def chunk_segments(
    segments: Iterable[Any],
    *,
    chunk_size: int | None = None,
    overlap: int | None = None,
    document_id: str | None = None,
    course_id: str | None = None,
    material_id: str | None = None,
) -> list[DocumentChunk]:
    """Chunk PDF pages, slides, transcripts, or normalized OCR/vision content."""
    configured = TextChunker.from_settings() if chunk_size is None or overlap is None else None
    chunker = TextChunker(
        chunk_size=chunk_size if chunk_size is not None else configured.chunk_size,
        overlap=overlap if overlap is not None else configured.overlap,
    )
    return chunker.chunk(
        segments,
        document_id=document_id,
        course_id=course_id,
        material_id=material_id,
    )


def chunk_pages(
    document_id: str,
    pages: list[ExtractedPage],
    chunk_size: int = 1000,
    overlap: int = 0,
) -> list[DocumentChunk]:
    """Backward-compatible PDF helper with optional page-local overlap."""
    return TextChunker(chunk_size=chunk_size, overlap=overlap).chunk(pages, document_id=document_id)
