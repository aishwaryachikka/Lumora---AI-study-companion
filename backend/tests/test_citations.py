"""Tests for PDF-compatible citations and validated cross-media references."""

import pytest

from app.services.citations import (
    Citation,
    InvalidCitationReferenceError,
    SourceCitation,
    citations_for,
    citations_for_evidence,
)
from app.services.chunking import SourceSegment, TextChunker


def _cross_media_chunks():
    return TextChunker().chunk(
        [
            SourceSegment(
                text="PDF evidence.",
                document_id="doc-pdf",
                source_id="source-pdf",
                source_filename="lecture.pdf",
                source_type="application/pdf",
                page_number=7,
                segment_id="page-7",
            ),
            SourceSegment(
                text="Slide evidence.",
                document_id="doc-ppt",
                source_id="source-ppt",
                source_filename="lecture.pptx",
                source_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                slide_number=4,
                segment_id="slide-4",
            ),
            SourceSegment(
                text="Video evidence.",
                document_id="doc-video",
                source_id="source-video",
                source_filename="lecture.mp4",
                source_type="video/mp4",
                timestamp_start_seconds=18.75,
                timestamp_end_seconds=23.0,
                segment_id="speech-2",
            ),
        ]
    )


def test_pdf_page_citation_preserves_explicit_source_location() -> None:
    """PDF citation metadata uses its original page and stable chunk IDs."""
    pdf = _cross_media_chunks()[0]

    citations = citations_for_evidence([pdf], [pdf.chunk_id])

    assert len(citations) == 1
    citation = citations[0]
    assert citation.chunk_id == pdf.chunk_id
    assert citation.document_id == "doc-pdf"
    assert citation.source_id == "source-pdf"
    assert citation.source_filename == "lecture.pdf"
    assert citation.source_type == "application/pdf"
    assert citation.page_number == 7
    assert citation.slide_number is None
    assert citation.location_type == "pdf_page"


def test_powerpoint_slide_citation_does_not_require_page_number() -> None:
    """PowerPoint references use slide numbers without requiring a PDF page."""
    slide = _cross_media_chunks()[1]

    citation = citations_for_evidence([slide], [slide.chunk_id])[0]

    assert citation.chunk_id == slide.chunk_id
    assert citation.source_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert citation.page_number is None
    assert citation.slide_number == 4
    assert citation.location_type == "powerpoint_slide"


def test_video_timestamp_citation_preserves_original_timeline() -> None:
    """Video/audio references preserve exact available start and end seconds."""
    video = _cross_media_chunks()[2]

    citation = citations_for_evidence([video], [video.chunk_id])[0]

    assert citation.source_filename == "lecture.mp4"
    assert citation.source_type == "video/mp4"
    assert citation.timestamp_start_seconds == 18.75
    assert citation.timestamp_end_seconds == 23.0
    assert citation.location_type == "media_timestamp"


def test_missing_source_metadata_stays_missing_and_non_navigable() -> None:
    """Unavailable IDs and locations remain absent instead of being fabricated."""
    chunk = TextChunker().chunk([SourceSegment(text="Unlocated evidence.")])[0]

    citation = citations_for_evidence([chunk], [chunk.chunk_id])[0]

    assert citation.chunk_id == chunk.chunk_id
    assert citation.document_id is None
    assert citation.source_filename is None
    assert citation.source_type is None
    assert citation.page_number is None
    assert citation.slide_number is None
    assert citation.timestamp_start_seconds is None
    assert citation.timestamp_end_seconds is None
    assert citation.location_type == "unspecified"
    assert "source_url" not in type(citation).model_fields


def test_unknown_chunk_reference_is_rejected() -> None:
    """A cited chunk ID must match an actual supplied evidence chunk."""
    with pytest.raises(InvalidCitationReferenceError, match="does not match"):
        citations_for_evidence(_cross_media_chunks(), ["invented-chunk-id"])


def test_duplicate_citation_ids_are_deduplicated_in_requested_order() -> None:
    """Repeated IDs produce one reference while preserving citation order."""
    pdf, slide, _video = _cross_media_chunks()

    citations = citations_for_evidence([pdf, slide], [slide.chunk_id, slide.chunk_id, pdf.chunk_id])

    assert [citation.chunk_id for citation in citations] == [slide.chunk_id, pdf.chunk_id]


def test_existing_pdf_citation_model_and_helper_remain_compatible() -> None:
    """Legacy PDF Citation fields and page-level deduplication stay unchanged."""
    pdf_chunks = TextChunker().chunk(
        [
            SourceSegment(text="First excerpt.", document_id="doc-pdf", page_number=2),
            SourceSegment(text="Second excerpt on same page.", document_id="doc-pdf", page_number=2),
            SourceSegment(text="Another page.", document_id="doc-pdf", page_number=3),
        ]
    )

    citations = citations_for(pdf_chunks)

    assert all(isinstance(citation, Citation) for citation in citations)
    assert [citation.model_dump() for citation in citations] == [
        {"document_id": "doc-pdf", "page_number": 2, "chunk_index": 0},
        {"document_id": "doc-pdf", "page_number": 3, "chunk_index": 2},
    ]


def test_source_citation_validates_timestamps_and_location_kind() -> None:
    """Explicit location descriptors must agree with actual location fields."""
    with pytest.raises(ValueError, match="must not precede"):
        SourceCitation(
            chunk_id="chunk-1",
            timestamp_start_seconds=30,
            timestamp_end_seconds=20,
        )
    with pytest.raises(ValueError, match="does not match"):
        SourceCitation(chunk_id="chunk-2", page_number=1, location_type="media_timestamp")
