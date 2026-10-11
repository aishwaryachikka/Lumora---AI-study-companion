"""Backward-compatible PDF citations and validated cross-media references."""

from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.chunking import DocumentChunk, TextChunk


class Citation(BaseModel):
    """Legacy PDF citation contract retained for existing callers."""

    document_id: str
    page_number: int
    chunk_index: int


CitationLocationType = Literal[
    "pdf_page",
    "powerpoint_slide",
    "media_timestamp",
    "multiple",
    "unspecified",
]


class SourceCitation(BaseModel):
    """Cross-media reference with only source identifiers and locations available."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(min_length=1)
    document_id: str | None = None
    source_id: str | None = None
    source_filename: str | None = None
    source_type: str | None = None
    course_id: str | None = None
    material_id: str | None = None
    chunk_index: int | None = Field(default=None, ge=0)
    page_number: int | None = Field(default=None, ge=1)
    slide_number: int | None = Field(default=None, ge=1)
    timestamp_start_seconds: float | None = Field(default=None, ge=0)
    timestamp_end_seconds: float | None = Field(default=None, ge=0)
    heading: str | None = None
    location_type: CitationLocationType = "unspecified"

    @model_validator(mode="after")
    def validate_location(self) -> "SourceCitation":
        """Derive the location kind only from present metadata and validate times."""
        if (
            self.timestamp_start_seconds is not None
            and self.timestamp_end_seconds is not None
            and self.timestamp_end_seconds < self.timestamp_start_seconds
        ):
            raise ValueError("timestamp_end_seconds must not precede the start timestamp")
        kinds = []
        if self.page_number is not None:
            kinds.append("pdf_page")
        if self.slide_number is not None:
            kinds.append("powerpoint_slide")
        if self.timestamp_start_seconds is not None or self.timestamp_end_seconds is not None:
            kinds.append("media_timestamp")
        expected: CitationLocationType = kinds[0] if len(kinds) == 1 else "multiple" if kinds else "unspecified"
        if self.location_type not in {"unspecified", expected}:
            raise ValueError("location_type does not match the supplied source location")
        object.__setattr__(self, "location_type", expected)
        return self

    @classmethod
    def from_chunk(cls, chunk: DocumentChunk) -> "SourceCitation":
        """Copy stable identifiers and actual location metadata from a chunk."""
        return cls(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            source_id=chunk.source_id,
            source_filename=chunk.source_filename,
            source_type=chunk.source_type,
            course_id=chunk.course_id,
            material_id=chunk.material_id,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            slide_number=chunk.slide_number,
            timestamp_start_seconds=chunk.timestamp_start_seconds,
            timestamp_end_seconds=chunk.timestamp_end_seconds,
            heading=chunk.heading,
        )


class InvalidCitationReferenceError(ValueError):
    """A requested citation does not resolve to a unique supplied chunk."""


def citations_for(chunks: list[TextChunk]) -> list[Citation]:
    """Build legacy PDF citations with the original required fields."""
    citations: list[Citation] = []
    seen: set[tuple[str | None, int | None]] = set()
    for chunk in chunks:
        key = (chunk.document_id, chunk.page_number)
        if key not in seen:
            citations.append(
                Citation(
                    document_id=chunk.document_id,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                )
            )
            seen.add(key)
    return citations


def citations_for_evidence(
    evidence: Sequence[DocumentChunk],
    cited_chunk_ids: Sequence[str],
) -> list[SourceCitation]:
    """Resolve cited IDs against supplied evidence and deduplicate in order.

    No source references are created from provider-supplied metadata. All
    location and source fields are copied from the matching ``DocumentChunk``.
    """
    chunks_by_id: dict[str, DocumentChunk] = {}
    for chunk in evidence:
        existing = chunks_by_id.get(chunk.chunk_id)
        if existing is not None and existing.model_dump() != chunk.model_dump():
            raise InvalidCitationReferenceError(
                "Supplied evidence contains conflicting metadata for one chunk ID."
            )
        chunks_by_id[chunk.chunk_id] = chunk

    citations: list[SourceCitation] = []
    seen: set[str] = set()
    for chunk_id in cited_chunk_ids:
        if chunk_id not in chunks_by_id:
            raise InvalidCitationReferenceError(
                "Citation chunk ID does not match supplied evidence."
            )
        if chunk_id in seen:
            continue
        citations.append(SourceCitation.from_chunk(chunks_by_id[chunk_id]))
        seen.add(chunk_id)
    return citations
