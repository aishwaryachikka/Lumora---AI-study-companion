"""Safe, page-aware PDF text extraction using PyMuPDF.

This module only reads document structure and text. It never executes PDF
JavaScript, launches embedded files, or follows external links.
"""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Literal, Protocol

import pymupdf as fitz

logger = logging.getLogger(__name__)


ProcessingStatus = Literal["completed", "completed_with_warnings", "requires_ocr", "empty"]
PageStatus = Literal["extracted", "no_text", "ocr_required"]


class DocumentProcessingError(Exception):
    """Base class for expected document validation and extraction failures."""

    code = "document_processing_error"
    status_code = 422


class PDFProcessingError(DocumentProcessingError):
    """Base class for expected PDF validation and extraction failures."""

    code = "pdf_processing_error"


class InvalidDocumentTypeError(PDFProcessingError):
    """The input is not a PDF based on its name, media type, or signature."""

    code = "invalid_document_type"
    status_code = 415


class DocumentTooLargeError(PDFProcessingError):
    """The input exceeds the configured upload size limit."""

    code = "document_too_large"
    status_code = 413


class PDFPageLimitError(PDFProcessingError):
    """The PDF has more pages than the configured processing limit."""

    code = "page_limit_exceeded"
    status_code = 413


class CorruptPDFError(PDFProcessingError):
    """The input could not be opened or read as a valid PDF."""

    code = "corrupt_pdf"
    status_code = 422


class PasswordProtectedPDFError(PDFProcessingError):
    """The PDF is encrypted and cannot be read without a password."""

    code = "password_protected_pdf"
    status_code = 422


@dataclass(frozen=True)
class ExtractedPage:
    """Text extracted from one page with its original one-based page number."""

    source_filename: str
    source_type: Literal["application/pdf"]
    page_number: int
    text: str
    status: PageStatus
    requires_ocr: bool


@dataclass(frozen=True)
class PDFExtractionResult:
    """Page-level PDF extraction and aggregate processing metadata."""

    source_filename: str
    source_type: Literal["application/pdf"]
    status: ProcessingStatus
    pages: list[ExtractedPage]
    page_count: int
    extracted_char_count: int


class DocumentProcessor(Protocol):
    """Contract implemented by format-specific document processors."""

    def process_path(self, path: Path, filename: str) -> PDFExtractionResult:
        """Extract source text while preserving page or slide locations."""
        ...


class PDFDocumentProcessor:
    """Extract PDF text page-by-page while enforcing configurable limits."""

    def __init__(
        self,
        max_upload_size_bytes: int = 25 * 1024 * 1024,
        max_pages: int = 500,
        max_extracted_chars: int = 2_000_000,
    ) -> None:
        if min(max_upload_size_bytes, max_pages, max_extracted_chars) < 1:
            raise ValueError("PDF processing limits must be positive")
        self.max_upload_size_bytes = max_upload_size_bytes
        self.max_pages = max_pages
        self.max_extracted_chars = max_extracted_chars

    def process_path(self, path: Path, filename: str) -> PDFExtractionResult:
        """Extract text from a temporary or trusted local PDF path.

        The source is checked by extension, PDF signature, and file size before
        it is opened. Text is extracted one page at a time and the PDF is closed
        promptly. Image-only pages are flagged for OCR; no OCR is performed.
        """
        safe_filename = Path(filename.replace("\\", "/")).name
        if Path(safe_filename).suffix.lower() != ".pdf":
            raise InvalidDocumentTypeError("Only PDF files are accepted.")

        try:
            file_size = path.stat().st_size
        except OSError as exc:
            raise CorruptPDFError("The uploaded PDF could not be read.") from exc
        if file_size > self.max_upload_size_bytes:
            raise DocumentTooLargeError("The PDF exceeds the configured upload size limit.")
        if file_size == 0:
            raise CorruptPDFError("The uploaded PDF is empty or invalid.")

        try:
            with path.open("rb") as file_handle:
                header = file_handle.read(1024)
            if b"%PDF-" not in header:
                raise InvalidDocumentTypeError("The uploaded file does not have a PDF signature.")

            with fitz.open(path) as document:
                if not document.is_pdf:
                    raise InvalidDocumentTypeError("The uploaded file is not a PDF document.")
                if document.needs_pass:
                    raise PasswordProtectedPDFError("Password-protected PDFs are not supported.")
                page_count = document.page_count
                if page_count == 0:
                    raise CorruptPDFError("The PDF contains no readable pages.")
                if page_count > self.max_pages:
                    raise PDFPageLimitError("The PDF exceeds the configured page processing limit.")

                pages: list[ExtractedPage] = []
                extracted_char_count = 0
                any_ocr_needed = False
                any_blank_page = False
                for index in range(page_count):
                    page = document.load_page(index)
                    text = page.get_text("text").strip()
                    extracted_char_count += len(text)
                    if extracted_char_count > self.max_extracted_chars:
                        raise PDFPageLimitError("The PDF exceeds the configured extracted text limit.")

                    no_text = not text
                    has_images = bool(page.get_images(full=True))
                    requires_ocr = no_text and has_images
                    any_ocr_needed |= requires_ocr
                    any_blank_page |= no_text and not has_images
                    page_status: PageStatus = "ocr_required" if requires_ocr else "no_text" if no_text else "extracted"
                    pages.append(
                        ExtractedPage(
                            source_filename=safe_filename,
                            source_type="application/pdf",
                            page_number=index + 1,
                            text=text,
                            status=page_status,
                            requires_ocr=requires_ocr,
                        )
                    )
        except PDFProcessingError:
            raise
        except Exception as exc:
            logger.exception("PDF extraction failed filename=%s", safe_filename)
            raise CorruptPDFError("The PDF is corrupted or could not be processed.") from exc

        if not pages or not extracted_char_count:
            overall_status: ProcessingStatus = "requires_ocr" if any_ocr_needed else "empty"
        elif any_ocr_needed or any_blank_page:
            overall_status = "completed_with_warnings" if extracted_char_count else "requires_ocr"
        else:
            overall_status = "completed"

        return PDFExtractionResult(
            source_filename=safe_filename,
            source_type="application/pdf",
            status=overall_status,
            pages=pages,
            page_count=len(pages),
            extracted_char_count=extracted_char_count,
        )
