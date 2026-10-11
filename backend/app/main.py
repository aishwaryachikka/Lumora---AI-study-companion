"""FastAPI application factory and application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router
from app.api.routes.tutor import router as tutor_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.services.tutor import TutorChatService, create_default_tutor_chat_service


def create_app(tutor_chat_service: TutorChatService | None = None) -> FastAPI:
    """Build the API application using environment-backed settings."""
    settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Release provider resources when the application shuts down."""
        try:
            yield
        finally:
            provider = application.state.tutor_chat_service.answer_generation.provider
            close = getattr(provider, "aclose", None)
            if callable(close):
                await close()

    application = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    application.state.tutor_chat_service = tutor_chat_service or create_default_tutor_chat_service(settings)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_exception_handlers(application)
    application.include_router(health_router, prefix="/api")
    application.include_router(documents_router, prefix="/api")
    application.include_router(tutor_router, prefix="/api")
    return application


app = create_app()
