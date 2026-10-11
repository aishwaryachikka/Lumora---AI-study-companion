"""Configuration parsing tests."""

from app.core.config import Settings
import pytest


def test_settings_use_defaults() -> None:
    """Settings have safe local defaults without environment configuration."""
    settings = Settings(_env_file=None)
    assert settings.environment == "development"
    assert settings.allowed_origins == ["http://localhost:3000"]


def test_comma_separated_cors_origins_are_parsed() -> None:
    """CORS origins can be configured using a comma-separated environment value."""
    settings = Settings(_env_file=None, cors_origins="https://app.example, http://localhost:3000")
    assert settings.allowed_origins == ["https://app.example", "http://localhost:3000"]


def test_chunking_size_and_overlap_are_configurable_and_validated() -> None:
    """Chunking defaults can be overridden and invalid overlap is rejected."""
    settings = Settings(_env_file=None, chunk_size_chars=800, chunk_overlap_chars=120)
    assert settings.chunk_size_chars == 800
    assert settings.chunk_overlap_chars == 120

    with pytest.raises(ValueError, match="CHUNK_OVERLAP_CHARS"):
        Settings(_env_file=None, chunk_size_chars=100, chunk_overlap_chars=100)


def test_embedding_provider_settings_are_environment_configurable() -> None:
    """Embedding endpoint, model, dimensions, and retry controls are settings."""
    settings = Settings(
        _env_file=None,
        embedding_provider="openai_compatible",
        embedding_api_url="https://example.test/v1/embeddings",
        embedding_model="sample-model",
        embedding_dimensions=768,
        embedding_batch_size=16,
    )

    assert settings.embedding_api_url == "https://example.test/v1/embeddings"
    assert settings.embedding_model == "sample-model"
    assert settings.embedding_dimensions == 768
    assert settings.embedding_batch_size == 16
