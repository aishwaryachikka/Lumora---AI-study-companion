"""Environment-backed application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables and an optional local .env."""

    app_name: str = "Lumora Study Companion API"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    max_upload_size_mb: int = Field(default=25, gt=0)
    max_pdf_pages: int = Field(default=500, gt=0)
    max_pptx_slides: int = Field(default=500, gt=0)
    max_pptx_processing_size_mb: int = Field(default=100, gt=0)
    max_pptx_archive_entries: int = Field(default=10_000, gt=0)
    max_extracted_chars: int = Field(default=2_000_000, gt=0)
    chunk_size_chars: int = Field(default=1000, gt=0)
    chunk_overlap_chars: int = Field(default=150, ge=0)
    max_media_duration_seconds: int = Field(default=1800, gt=0)
    max_extracted_audio_size_mb: int = Field(default=100, gt=0)
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    ffmpeg_timeout_seconds: float = Field(default=300, gt=0)
    stt_provider: str = "openai_compatible"
    stt_api_url: str = "https://api.openai.com/v1/audio/transcriptions"
    stt_api_key: SecretStr | None = None
    stt_model: str = "whisper-1"
    stt_timeout_seconds: float = Field(default=300, gt=0)
    embedding_provider: str = "openai_compatible"
    embedding_api_url: str = "https://api.openai.com/v1/embeddings"
    embedding_api_key: SecretStr | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int | None = Field(default=1536, gt=0)
    embedding_batch_size: int = Field(default=64, gt=0, le=2048)
    embedding_timeout_seconds: float = Field(default=30, gt=0)
    embedding_max_retries: int = Field(default=3, ge=1, le=10)
    embedding_retry_base_seconds: float = Field(default=0.25, ge=0, le=30)
    embedding_retry_max_seconds: float = Field(default=4, ge=0, le=60)
    answer_provider: Literal["gemini", "mock", "unconfigured"] = "gemini"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: float = Field(default=60, gt=0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> "Settings":
        """Ensure the configured overlap leaves room for forward progress."""
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than CHUNK_SIZE_CHARS")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        """Return configured CORS origins from a comma-separated setting."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        """Return the upload limit in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_pptx_processing_size_bytes(self) -> int:
        """Return the PPTX uncompressed package size limit in bytes."""
        return self.max_pptx_processing_size_mb * 1024 * 1024

    @property
    def max_extracted_audio_size_bytes(self) -> int:
        """Return the temporary extracted-audio limit in bytes."""
        return self.max_extracted_audio_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return cached process-wide settings."""
    return Settings()
