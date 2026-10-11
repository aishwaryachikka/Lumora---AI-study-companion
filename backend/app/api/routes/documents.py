"""Routes for document upload and ingestion."""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.schemas.documents import (
    MediaTranscriptionResponse,
    PDFIngestionResponse,
    PowerPointIngestionResponse,
)
from app.core.config import get_settings
from app.services.document_processing import (
    DocumentProcessingError,
    DocumentTooLargeError,
    InvalidDocumentTypeError,
    PDFDocumentProcessor,
    PDFPageLimitError,
)
from app.services.powerpoint_processing import (
    POWERPOINT_MIME_TYPE,
    InvalidPowerPointTypeError,
    PowerPointDocumentProcessor,
    PowerPointTooLargeError,
)
from app.services.video_processing import (
    SUPPORTED_MEDIA_TYPES,
    LectureMediaProcessor,
    MediaTooLargeError,
    OpenAICompatibleTranscriber,
    TranscriptionConfigurationError,
    UnsupportedMediaTypeError,
    is_supported_media_type,
)
from app.services.tutor import TutorChatService, TutorIndexingError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])
READ_CHUNK_BYTES = 1024 * 1024


@router.post("/upload", response_model=PDFIngestionResponse)
async def upload_pdf(file: UploadFile = File(...)) -> PDFIngestionResponse:
    """Stream a PDF to a private temporary file and extract its page text."""
    settings = get_settings()
    if Path((file.filename or "").replace("\\", "/")).suffix.lower() != ".pdf":
        raise InvalidDocumentTypeError("Only PDF files are accepted.")
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise InvalidDocumentTypeError("The uploaded file must use the PDF media type.")

    processor = PDFDocumentProcessor(
        max_upload_size_bytes=settings.max_upload_size_bytes,
        max_pages=settings.max_pdf_pages,
        max_extracted_chars=settings.max_extracted_chars,
    )
    total_bytes = 0
    filename = file.filename or "upload.pdf"
    try:
        with tempfile.TemporaryDirectory(prefix="lumora-pdf-") as temp_dir:
            temp_path = Path(temp_dir) / "upload.pdf"
            with temp_path.open("wb") as destination:
                while data := await file.read(READ_CHUNK_BYTES):
                    total_bytes += len(data)
                    if total_bytes > settings.max_upload_size_bytes:
                        raise DocumentTooLargeError("The PDF exceeds the configured upload size limit.")
                    destination.write(data)
            result = await run_in_threadpool(processor.process_path, temp_path, filename)
        logger.info(
            "PDF ingestion finished filename=%s status=%s pages=%d",
            Path(filename.replace("\\", "/")).name,
            result.status,
            result.page_count,
        )
        return PDFIngestionResponse.model_validate(result)
    except (DocumentTooLargeError, InvalidDocumentTypeError, PDFPageLimitError):
        raise
    except OSError as exc:
        logger.exception("Temporary PDF processing failed")
        raise HTTPException(status_code=500, detail="PDF processing failed.") from exc
    finally:
        await file.close()


@router.post("/upload/pptx", response_model=PowerPointIngestionResponse)
async def upload_pptx(file: UploadFile = File(...)) -> PowerPointIngestionResponse:
    """Stream and extract a PPTX without mixing image analysis into parsing."""
    settings = get_settings()
    filename = file.filename or "upload.pptx"
    if Path(filename.replace("\\", "/")).suffix.lower() != ".pptx":
        raise InvalidPowerPointTypeError("Only .pptx files are accepted.")
    if file.content_type not in {POWERPOINT_MIME_TYPE, "application/octet-stream"}:
        raise InvalidPowerPointTypeError("The uploaded file must use the PPTX media type.")

    processor = PowerPointDocumentProcessor(
        max_upload_size_bytes=settings.max_upload_size_bytes,
        max_slides=settings.max_pptx_slides,
        max_extracted_chars=settings.max_extracted_chars,
        max_processing_size_bytes=settings.max_pptx_processing_size_bytes,
        max_archive_entries=settings.max_pptx_archive_entries,
    )
    total_bytes = 0
    try:
        with tempfile.TemporaryDirectory(prefix="lumora-pptx-") as temp_dir:
            temp_path = Path(temp_dir) / "upload.pptx"
            with temp_path.open("wb") as destination:
                while data := await file.read(READ_CHUNK_BYTES):
                    total_bytes += len(data)
                    if total_bytes > settings.max_upload_size_bytes:
                        raise PowerPointTooLargeError("The PPTX exceeds the configured upload size limit.")
                    destination.write(data)
            result = await run_in_threadpool(processor.process_path, temp_path, filename)
        logger.info(
            "PPTX ingestion finished filename=%s status=%s slides=%d images=%d",
            Path(filename.replace("\\", "/")).name,
            result.status,
            result.slide_count,
            len(result.images),
        )
        return PowerPointIngestionResponse(
            source_filename=result.source_filename,
            source_type=result.source_type,
            status=result.status,
            slides=result.slides,
            images=result.images,
            slide_count=result.slide_count,
            extracted_char_count=result.extracted_char_count,
        )
    except DocumentProcessingError:
        raise
    except OSError as exc:
        logger.exception("Temporary PPTX processing failed")
        raise HTTPException(status_code=500, detail="PPTX processing failed.") from exc
    finally:
        await file.close()


@router.post("/upload/media", response_model=MediaTranscriptionResponse)
async def upload_lecture_media(
    request: Request,
    file: UploadFile = File(...),
    document_id: str | None = Form(default=None),
    source_id: str | None = Form(default=None),
    course_id: str | None = Form(default=None),
) -> MediaTranscriptionResponse:
    """Stream lecture audio/video, extract audio, and return timestamped text."""
    settings = get_settings()
    filename = file.filename or "upload"
    extension = Path(filename.replace("\\", "/")).suffix.lower()
    expected_type = SUPPORTED_MEDIA_TYPES.get(extension)
    if expected_type is None:
        raise UnsupportedMediaTypeError("The uploaded audio or video format is not supported.")
    if not is_supported_media_type(extension, file.content_type):
        raise UnsupportedMediaTypeError("The uploaded media type does not match its file format.")
    if settings.stt_provider not in {"openai_compatible", "whisper_compatible"}:
        raise TranscriptionConfigurationError("The configured speech-to-text provider is unsupported.")

    api_key = settings.stt_api_key.get_secret_value() if settings.stt_api_key else None
    transcriber = OpenAICompatibleTranscriber(
        api_url=settings.stt_api_url,
        model=settings.stt_model,
        api_key=api_key,
        timeout_seconds=settings.stt_timeout_seconds,
    )
    processor = LectureMediaProcessor(
        transcriber,
        max_file_size_bytes=settings.max_upload_size_bytes,
        max_duration_seconds=settings.max_media_duration_seconds,
        max_audio_size_bytes=settings.max_extracted_audio_size_bytes,
        ffmpeg_path=settings.ffmpeg_path,
        ffprobe_path=settings.ffprobe_path,
        ffmpeg_timeout_seconds=settings.ffmpeg_timeout_seconds,
    )
    total_bytes = 0
    safe_extension = extension
    try:
        with tempfile.TemporaryDirectory(prefix="lumora-media-") as temp_dir:
            media_path = Path(temp_dir) / f"upload{safe_extension}"
            with media_path.open("wb") as destination:
                while data := await file.read(READ_CHUNK_BYTES):
                    total_bytes += len(data)
                    if total_bytes > settings.max_upload_size_bytes:
                        raise MediaTooLargeError("The media exceeds the configured upload size limit.")
                    destination.write(data)
            result = await run_in_threadpool(
                processor.process_path,
                media_path,
                filename,
                document_id=document_id,
                source_id=source_id,
            )
        tutor_service: TutorChatService = request.app.state.tutor_chat_service
        await tutor_service.index_segments(result.source_segments, course_id=course_id)
        logger.info(
            "Lecture media ingestion finished filename=%s status=%s segments=%d duration_seconds=%.3f",
            Path(filename.replace("\\", "/")).name,
            result.status,
            len(result.segments),
            result.duration_seconds,
        )
        return MediaTranscriptionResponse(
            source_filename=result.source_filename,
            source_type=result.source_type,
            status=result.status,
            duration_seconds=result.duration_seconds,
            segments=[
                {
                    "source_filename": item.source_filename,
                    "source_type": item.source_type,
                    "text": item.text,
                    "start_seconds": item.start_seconds,
                    "end_seconds": item.end_seconds,
                    "formatted_start_time": item.formatted_start_time,
                    "formatted_end_time": item.formatted_end_time,
                    "segment_id": item.segment_id,
                }
                for item in result.segments
            ],
        )
    except DocumentProcessingError:
        raise
    except TutorIndexingError as exc:
        logger.exception("Transcript indexing failed filename=%s", Path(filename.replace("\\", "/")).name)
        raise HTTPException(
            status_code=503,
            detail="The transcript was created but could not be indexed for tutor retrieval.",
        ) from exc
    except OSError as exc:
        logger.exception("Temporary lecture media processing failed")
        raise HTTPException(status_code=500, detail="Media processing failed.") from exc
    finally:
        await file.close()
