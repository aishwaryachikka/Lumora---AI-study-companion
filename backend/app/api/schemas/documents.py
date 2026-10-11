"""Document ingestion response models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ExtractedPageResponse(BaseModel):
    """Extracted text and status for one original PDF page."""

    model_config = ConfigDict(from_attributes=True)

    source_filename: str
    source_type: Literal["application/pdf"]
    page_number: int
    text: str
    status: Literal["extracted", "no_text", "ocr_required"]
    requires_ocr: bool


class PDFIngestionResponse(BaseModel):
    """Aggregate PDF processing result."""

    model_config = ConfigDict(from_attributes=True)

    source_filename: str
    source_type: Literal["application/pdf"]
    status: Literal["completed", "completed_with_warnings", "requires_ocr", "empty"]
    pages: list[ExtractedPageResponse]
    page_count: int
    extracted_char_count: int


class ExtractedSlideResponse(BaseModel):
    """Text and optional title extracted from a one-based presentation slide."""

    model_config = ConfigDict(from_attributes=True)

    source_filename: str
    source_type: Literal["application/vnd.openxmlformats-officedocument.presentationml.presentation"]
    slide_number: int
    title: str | None
    text: str
    status: Literal["extracted", "no_text"]
    image_count: int


class ExtractedSlideImageResponse(BaseModel):
    """Image asset metadata linked to its original presentation slide."""

    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    source_filename: str
    source_type: Literal["application/vnd.openxmlformats-officedocument.presentationml.presentation"]
    slide_number: int
    image_index: int
    asset_filename: str
    content_type: str
    size_bytes: int
    sha256: str


class PowerPointIngestionResponse(BaseModel):
    """Aggregate PPTX extraction response; image bytes stay in the service result."""

    source_filename: str
    source_type: Literal["application/vnd.openxmlformats-officedocument.presentationml.presentation"]
    status: Literal["completed", "completed_with_warnings", "empty"]
    slides: list[ExtractedSlideResponse]
    images: list[ExtractedSlideImageResponse]
    slide_count: int
    extracted_char_count: int


class TranscriptionSegmentResponse(BaseModel):
    """Timestamped transcript text and the media file it came from."""

    source_filename: str
    source_type: str
    text: str
    start_seconds: float
    end_seconds: float
    formatted_start_time: str
    formatted_end_time: str
    segment_id: str


class MediaTranscriptionResponse(BaseModel):
    """Speech transcription result for an uploaded audio/video file."""

    source_filename: str
    source_type: str
    status: Literal["transcribed", "no_speech"]
    duration_seconds: float
    segments: list[TranscriptionSegmentResponse]
