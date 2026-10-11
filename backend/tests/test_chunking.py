"""Tests for reusable source-aware text chunking."""

from app.services.chunking import (
    DocumentChunk,
    ExtractedContent,
    SourceSegment,
    TextChunk,
    TextChunker,
    chunk_segments,
)
from app.services.document_processing import ExtractedPage
from app.services.powerpoint_processing import ExtractedSlide, POWERPOINT_MIME_TYPE
from app.services.video_processing import TranscriptionSegment


def test_short_text_is_returned_as_one_chunk() -> None:
    """Short segments produce one chunk with stable source metadata."""
    segment = SourceSegment(
        text="A short lesson excerpt.",
        source_filename="lesson.pdf",
        source_type="application/pdf",
        document_id="doc-123",
        page_number=2,
    )

    chunks = TextChunker(chunk_size=100, overlap=10).chunk([segment])

    assert len(chunks) == 1
    assert chunks[0].text == "A short lesson excerpt."
    assert chunks[0].chunk_id.startswith("chunk_")
    assert chunks[0].document_id == "doc-123"
    assert chunks[0].page_number == 2


def test_long_text_is_split_with_bounded_chunk_sizes() -> None:
    """Long source text is split into chunks no larger than the configured size."""
    text = "0123456789" * 5

    chunks = TextChunker(chunk_size=16, overlap=4).chunk(
        [SourceSegment(text=text, source_filename="chapter.pdf", page_number=4)]
    )

    assert len(chunks) > 1
    assert all(0 < len(chunk.text) <= 16 for chunk in chunks)
    assert all(chunk.page_number == 4 for chunk in chunks)
    assert "".join([chunks[0].text] + [chunk.text[4:] for chunk in chunks[1:]]) == text


def test_adjacent_chunks_repeat_the_configured_overlap() -> None:
    """The trailing source characters appear at the start of the next chunk."""
    chunks = TextChunker(chunk_size=12, overlap=4).chunk(
        [SourceSegment(text="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")]
    )

    assert len(chunks) == 4
    for previous, current in zip(chunks, chunks[1:]):
        assert previous.text[-4:] == current.text[:4]


def test_empty_or_whitespace_text_is_skipped() -> None:
    """Empty segments do not produce invalid or empty embedding inputs."""
    chunks = chunk_segments(
        [SourceSegment(text=""), SourceSegment(text=" \n\t ")],
        chunk_size=20,
        overlap=0,
    )

    assert chunks == []


def test_pdf_slide_and_video_source_metadata_are_preserved() -> None:
    """Chunks retain source IDs and format-specific page, slide, or time data."""
    pdf_page = ExtractedPage(
        source_filename="biology.pdf",
        source_type="application/pdf",
        page_number=3,
        text="PDF page text",
        status="extracted",
        requires_ocr=False,
    )
    slide = SourceSegment(
        text="Slide content",
        source_filename="lecture.pptx",
        source_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        document_id="doc-slides",
        source_id="source-slides",
        slide_number=7,
    )
    video = SourceSegment(
        text="Transcript caption",
        source_filename="lecture.mp4",
        source_type="video/mp4",
        document_id="doc-video",
        source_id="source-video",
        segment_id="caption-8",
        timestamp_start_seconds=42.5,
        timestamp_end_seconds=48.0,
    )

    pdf_chunk = TextChunker().chunk([pdf_page], document_id="doc-pdf")[0]
    slide_chunk = TextChunker().chunk([slide])[0]
    video_chunk = TextChunker().chunk([video])[0]

    assert (pdf_chunk.document_id, pdf_chunk.source_filename, pdf_chunk.page_number) == (
        "doc-pdf",
        "biology.pdf",
        3,
    )
    assert pdf_chunk.source_type == "application/pdf"
    assert slide_chunk.source_id == "source-slides"
    assert slide_chunk.source_filename == "lecture.pptx"
    assert slide_chunk.source_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert slide_chunk.slide_number == 7
    assert video_chunk.source_id == "source-video"
    assert video_chunk.source_type == "video/mp4"
    assert video_chunk.segment_id == "caption-8"
    assert video_chunk.timestamp_start_seconds == 42.5
    assert video_chunk.timestamp_end_seconds == 48.0


def test_chunk_ids_are_stable_for_same_source_and_offsets() -> None:
    """Repeated processing of the same source data yields identical chunk IDs."""
    segment = SourceSegment(text="repeatable", document_id="doc-42", source_id="file-42")
    chunker = TextChunker(chunk_size=5, overlap=1)

    first = chunker.chunk([segment])
    second = chunker.chunk([segment])

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert len({chunk.chunk_id for chunk in first}) == len(first)


def test_document_chunk_is_typed_and_missing_metadata_stays_missing() -> None:
    """The normalized model is reusable without inventing unavailable metadata."""
    chunk = TextChunker().chunk([SourceSegment(text="An excerpt")])[0]

    assert isinstance(chunk, DocumentChunk)
    assert TextChunk is DocumentChunk
    assert chunk.chunk_id
    assert chunk.text == "An excerpt"
    assert chunk.document_id is None
    assert chunk.source_id is None
    assert chunk.source_filename is None
    assert chunk.source_type is None
    assert chunk.page_number is None
    assert chunk.slide_number is None
    assert chunk.timestamp_start_seconds is None
    assert chunk.timestamp_end_seconds is None


def test_heading_and_topic_metadata_are_preserved() -> None:
    """Optional heading and topic metadata survive chunking."""
    chunks = TextChunker(chunk_size=8, overlap=2).chunk(
        [SourceSegment(text="A longer section on cells", heading="Cell Theory", topic="Biology")]
    )

    assert len(chunks) > 1
    assert all(chunk.heading == "Cell Theory" for chunk in chunks)
    assert all(chunk.topic == "Biology" for chunk in chunks)


def test_extracted_content_is_a_validated_shared_pydantic_schema() -> None:
    """The reusable input model carries source IDs and extraction quality data."""
    content = ExtractedContent(
        text="Image description: a labeled cell diagram.",
        source_filename="slides.pptx",
        source_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        course_id="course-1",
        material_id="material-2",
        slide_number=4,
        content_kind="vision_description",
        extraction_warnings=["Generated by configured vision adapter."],
        is_incomplete=True,
    )

    chunk = chunk_segments([content], chunk_size=100, overlap=0)[0]

    assert chunk.course_id == "course-1"
    assert chunk.material_id == "material-2"
    assert chunk.slide_number == 4
    assert chunk.content_kind == "vision_description"
    assert chunk.extraction_warnings == ["Generated by configured vision adapter."]
    assert chunk.is_incomplete is True


def test_sentence_and_paragraph_boundaries_are_preferred() -> None:
    """A chunk ends at a readable boundary when one fits under the size limit."""
    text = "First paragraph has a complete sentence.\n\nSecond paragraph follows here."

    chunks = TextChunker(chunk_size=48, overlap=0).chunk([SourceSegment(text=text)])

    assert len(chunks) == 2
    assert chunks[0].text == "First paragraph has a complete sentence."
    assert chunks[1].text == "Second paragraph follows here."


def test_timestamp_metadata_survives_long_video_chunking() -> None:
    """Every chunk from a transcript segment retains its original timeline span."""
    content = ExtractedContent(
        text="A transcript sentence. " * 15,
        source_filename="lecture.mp4",
        source_type="video/mp4",
        document_id="video-doc",
        course_id="course-video",
        material_id="video-material",
        segment_id="speech-12",
        timestamp_start_seconds=83.25,
        timestamp_end_seconds=109.75,
    )

    chunks = chunk_segments([content], chunk_size=70, overlap=12)

    assert len(chunks) > 1
    assert all(chunk.timestamp_start_seconds == 83.25 for chunk in chunks)
    assert all(chunk.timestamp_end_seconds == 109.75 for chunk in chunks)
    assert all(chunk.segment_id == "speech-12" for chunk in chunks)
    assert all(chunk.course_id == "course-video" for chunk in chunks)


def test_context_ids_fill_only_missing_values() -> None:
    """Caller context fills absent IDs and does not replace extracted IDs."""
    chunks = chunk_segments(
        [SourceSegment(text="Excerpt", document_id="doc-original", course_id="course-original")],
        document_id="doc-context",
        course_id="course-context",
        material_id="material-context",
        chunk_size=50,
        overlap=0,
    )

    assert chunks[0].document_id == "doc-original"
    assert chunks[0].course_id == "course-original"
    assert chunks[0].material_id == "material-context"


def test_processor_result_shapes_normalize_directly() -> None:
    """PPT slide and video transcript objects can be passed without adapters."""
    slide = ExtractedSlide(
        source_filename="lecture.pptx",
        source_type=POWERPOINT_MIME_TYPE,
        slide_number=5,
        title="Cell Structure",
        text="The cell has a membrane.",
        status="extracted",
        image_count=1,
    )
    transcript = TranscriptionSegment(
        text="The lecture begins.",
        start_seconds=12.0,
        end_seconds=15.5,
        formatted_start_time="00:00:12.000",
        formatted_end_time="00:00:15.500",
        source_filename="lecture.mp4",
        source_type="video/mp4",
        segment_id="transcript-1",
    )

    slide_chunk = TextChunker().chunk([slide])[0]
    video_chunk = TextChunker().chunk([transcript])[0]

    assert slide_chunk.slide_number == 5
    assert slide_chunk.heading == "Cell Structure"
    assert slide_chunk.is_incomplete is True
    assert "not analyzed" in slide_chunk.extraction_warnings[0]
    assert (video_chunk.timestamp_start_seconds, video_chunk.timestamp_end_seconds) == (12.0, 15.5)
    assert video_chunk.segment_id == "transcript-1"
