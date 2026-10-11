"""Tests for page-aware PDF extraction and rejection behavior."""

from pathlib import Path

import pymupdf as fitz
import pytest

from app.services.document_processing import (
    CorruptPDFError,
    DocumentTooLargeError,
    InvalidDocumentTypeError,
    PDFDocumentProcessor,
    PDFPageLimitError,
)


def write_pdf(path: Path, page_texts: list[str | None]) -> Path:
    """Create a small PDF fixture with optional text on each page."""
    document = fitz.open()
    for text in page_texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path


def test_extracts_text_and_source_metadata_from_text_pdf(tmp_path: Path) -> None:
    """A text PDF returns its source information and extracted page text."""
    path = write_pdf(tmp_path / "lesson.pdf", ["Cell structure"])

    result = PDFDocumentProcessor().process_path(path, "lesson.pdf")

    assert result.status == "completed"
    assert result.source_filename == "lesson.pdf"
    assert result.source_type == "application/pdf"
    assert result.pages[0].page_number == 1
    assert result.pages[0].text == "Cell structure"
    assert result.pages[0].status == "extracted"
    assert not result.pages[0].requires_ocr


def test_multipage_pdf_preserves_original_page_numbers(tmp_path: Path) -> None:
    """Each extracted page remains linked to its original one-based number."""
    path = write_pdf(tmp_path / "lecture.pdf", ["First", "Second", "Third"])

    result = PDFDocumentProcessor().process_path(path, "lecture.pdf")

    assert [page.page_number for page in result.pages] == [1, 2, 3]
    assert [page.text for page in result.pages] == ["First", "Second", "Third"]


def test_empty_pdf_is_not_reported_as_completed(tmp_path: Path) -> None:
    """A genuinely blank PDF receives an explicit empty status."""
    path = write_pdf(tmp_path / "blank.pdf", [None, None])

    result = PDFDocumentProcessor().process_path(path, "blank.pdf")

    assert result.status == "empty"
    assert [page.status for page in result.pages] == ["no_text", "no_text"]
    assert all(page.text == "" for page in result.pages)


def test_image_only_page_is_flagged_for_ocr_without_claiming_ocr(tmp_path: Path) -> None:
    """An image-only page is flagged as needing OCR; no OCR is claimed."""
    path = tmp_path / "scan.pdf"
    document = fitz.open()
    page = document.new_page()
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 32, 32), 0)
    pixmap.clear_with(200)
    page.insert_image(page.rect, stream=pixmap.tobytes("png"))
    document.save(path)
    document.close()

    result = PDFDocumentProcessor().process_path(path, "scan.pdf")

    assert result.status == "requires_ocr"
    assert result.pages[0].status == "ocr_required"
    assert result.pages[0].requires_ocr is True
    assert result.pages[0].text == ""


def test_corrupt_pdf_raises_a_safe_processing_error(tmp_path: Path) -> None:
    """Corrupt content is rejected with a typed error rather than empty success."""
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.7\nnot a valid pdf")

    with pytest.raises(CorruptPDFError):
        PDFDocumentProcessor().process_path(path, "broken.pdf")


def test_unexpected_extraction_failure_is_wrapped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected parser failures become a safe application-level error."""
    path = write_pdf(tmp_path / "parser-failure.pdf", ["Text"])

    def fail_open(*args: object, **kwargs: object) -> None:
        raise RuntimeError("parser internals")

    monkeypatch.setattr("app.services.document_processing.fitz.open", fail_open)
    with pytest.raises(CorruptPDFError, match="could not be processed"):
        PDFDocumentProcessor().process_path(path, "parser-failure.pdf")


def test_invalid_file_type_is_rejected(tmp_path: Path) -> None:
    """Non-PDF file extensions are rejected before document parsing."""
    path = tmp_path / "notes.txt"
    path.write_text("This is not a PDF", encoding="utf-8")

    with pytest.raises(InvalidDocumentTypeError):
        PDFDocumentProcessor().process_path(path, "notes.txt")


def test_size_and_page_limits_are_enforced(tmp_path: Path) -> None:
    """Configured upload-size and page-count limits fail clearly."""
    path = write_pdf(tmp_path / "two-pages.pdf", ["One", "Two"])

    with pytest.raises(DocumentTooLargeError):
        PDFDocumentProcessor(max_upload_size_bytes=1).process_path(path, "two-pages.pdf")
    with pytest.raises(PDFPageLimitError):
        PDFDocumentProcessor(max_pages=1).process_path(path, "two-pages.pdf")
