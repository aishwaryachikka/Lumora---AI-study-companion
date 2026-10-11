"""Consistent, client-safe API exception handling."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.document_processing import DocumentProcessingError

logger = logging.getLogger(__name__)


def register_exception_handlers(application: FastAPI) -> None:
    """Register stable error response handlers on an application."""

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        del request
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Request validation failed."}})

    @application.exception_handler(DocumentProcessingError)
    async def document_error_handler(request: Request, exc: DocumentProcessingError) -> JSONResponse:
        del request
        logger.warning("Document processing rejected code=%s", exc.code)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": str(exc)}},
        )

    @application.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error on %s", request.url.path, exc_info=exc)
        content: dict[str, Any] = {"error": {"code": "internal_error", "message": "An internal error occurred."}}
        return JSONResponse(status_code=500, content=content)
