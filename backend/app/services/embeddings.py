"""Configurable embedding providers and validated chunk embedding service.

This module is deliberately independent from extraction, retrieval, and answer
generation. It returns storage-ready vectors with enough metadata for callers
to enforce a single model and dimensionality per vector collection.
"""

import asyncio
import hashlib
import logging
import math
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings

from app.services.chunking import DocumentChunk

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


class EmbeddingError(Exception):
    """Base error for embedding configuration, provider, and response issues."""


class EmbeddingConfigurationError(EmbeddingError):
    """The selected provider is missing or has invalid configuration."""


class EmbeddingProviderError(EmbeddingError):
    """The embedding provider failed after bounded retry handling."""


class MalformedEmbeddingResponseError(EmbeddingError):
    """The provider returned vectors that do not match the requested inputs."""


class IncompatibleEmbeddingError(EmbeddingError):
    """An embedding model or dimension conflicts with the configured vector set."""


class EmbeddingProvider(Protocol):
    """Contract for providers that return one vector per input text in order."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Convert a batch of texts to vectors, preserving input order."""
        ...


class OpenAICompatibleEmbeddingProvider:
    """Client for endpoints implementing the OpenAI embeddings request format."""

    def __init__(
        self,
        *,
        api_url: str,
        model_id: str,
        api_key: str | None,
        dimensions: int | None = None,
        timeout_seconds: float = 30,
        max_retries: int = 3,
        retry_base_seconds: float = 0.25,
        retry_max_seconds: float = 4,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_url.strip() or not model_id.strip():
            raise EmbeddingConfigurationError("Embedding API URL and model ID are required.")
        if timeout_seconds <= 0 or max_retries < 1 or retry_base_seconds < 0 or retry_max_seconds < 0:
            raise EmbeddingConfigurationError("Embedding timeout and retry configuration is invalid.")
        self.api_url = api_url
        self.model_id = model_id
        self.api_key = api_key
        self.dimensions = dimensions
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds
        self.transport = transport

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Call the configured endpoint, retrying transient failures only."""
        if not texts:
            return []
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model_id, "input": texts}
        if self.dimensions is not None:
            payload["dimensions"] = self.dimensions

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds,
                    transport=self.transport,
                ) as client:
                    response = await client.post(self.api_url, headers=headers, json=payload)
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    if attempt + 1 < self.max_retries:
                        await self._wait_before_retry(attempt)
                        continue
                    raise EmbeddingProviderError(
                        f"Embedding provider returned retryable HTTP {response.status_code}."
                    )
                if response.is_error:
                    raise EmbeddingProviderError(
                        f"Embedding provider returned HTTP {response.status_code}."
                    )
                try:
                    body = response.json()
                    data = body["data"]
                    if not isinstance(data, list) or len(data) != len(texts):
                        raise ValueError("response count mismatch")
                    indexed: dict[int, list[float]] = {}
                    for item in data:
                        index = item["index"]
                        vector = item["embedding"]
                        if isinstance(index, bool) or not isinstance(index, int) or index in indexed:
                            raise ValueError("invalid response index")
                        if not isinstance(vector, list) or not vector:
                            raise ValueError("invalid vector")
                        indexed[index] = vector
                    if set(indexed) != set(range(len(texts))):
                        raise ValueError("response indices are incomplete")
                    return [indexed[index] for index in range(len(texts))]
                except (KeyError, TypeError, ValueError) as exc:
                    raise MalformedEmbeddingResponseError(
                        "Embedding provider returned a malformed response."
                    ) from exc
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt + 1 < self.max_retries:
                    await self._wait_before_retry(attempt)
                    continue
                logger.warning("Embedding provider exhausted retries after a network failure.")
                raise EmbeddingProviderError("Embedding provider request failed after retries.") from exc
        raise EmbeddingProviderError("Embedding provider request failed after retries.")

    async def _wait_before_retry(self, attempt: int) -> None:
        """Apply bounded exponential backoff without logging request content."""
        delay = min(self.retry_base_seconds * (2**attempt), self.retry_max_seconds)
        if delay:
            await asyncio.sleep(delay)


class MockEmbeddingProvider:
    """Deterministic local provider for tests and offline development only."""

    def __init__(self, dimensions: int = 8) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return reproducible normalized hash-derived vectors."""
        self.calls.append(list(texts))
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.shake_256(text.encode("utf-8")).digest(self.dimensions * 4)
            values = [int.from_bytes(digest[i : i + 4], "big") / (2**32 - 1) * 2 - 1
                      for i in range(0, len(digest), 4)]
            norm = math.sqrt(sum(value * value for value in values)) or 1.0
            vectors.append([value / norm for value in values])
        return vectors


class EmbeddedChunk(BaseModel):
    """Chunk vector and metadata required to validate its vector collection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    embedding_dimensions: int = Field(gt=0)
    content_hash: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_embedding(self) -> "EmbeddedChunk":
        """Validate finite values and agreement between vector and metadata."""
        if len(self.embedding) != self.embedding_dimensions:
            raise ValueError("embedding_dimensions must match the vector length")
        if any(not math.isfinite(value) for value in self.embedding):
            raise ValueError("embedding values must be finite")
        return self


class EmbeddingService:
    """Batch, validate, and reuse embeddings for normalized document chunks."""

    def __init__(
        self,
        provider: EmbeddingProvider,
        *,
        model_id: str,
        expected_dimensions: int | None = None,
        batch_size: int = 64,
    ) -> None:
        if not model_id.strip():
            raise EmbeddingConfigurationError("Embedding model ID is required.")
        if expected_dimensions is not None and expected_dimensions < 1:
            raise EmbeddingConfigurationError("Embedding dimensions must be positive.")
        if batch_size < 1:
            raise EmbeddingConfigurationError("Embedding batch size must be positive.")
        self.provider = provider
        self.model_id = model_id
        self.expected_dimensions = expected_dimensions
        self.batch_size = batch_size
        self._observed_dimensions: int | None = expected_dimensions

    @property
    def is_mock(self) -> bool:
        """Whether this service uses deterministic, non-semantic test vectors."""
        return isinstance(self.provider, MockEmbeddingProvider)

    @classmethod
    def from_settings(cls, settings: BaseSettings | None = None) -> "EmbeddingService":
        """Construct the configured provider and service from environment settings."""
        if settings is None:
            from app.core.config import get_settings

            settings = get_settings()
        provider_name = getattr(settings, "embedding_provider", "openai_compatible")
        model_id = getattr(settings, "embedding_model", "text-embedding-3-small")
        expected_dimensions = getattr(settings, "embedding_dimensions", 1536)
        batch_size = getattr(settings, "embedding_batch_size", 64)
        if provider_name == "mock":
            model_id = f"mock-hash-shake-256-v1-{expected_dimensions or 8}d"
            provider: EmbeddingProvider = MockEmbeddingProvider(expected_dimensions or 8)
        elif provider_name == "openai_compatible":
            secret = getattr(settings, "embedding_api_key", None)
            api_key = secret.get_secret_value() if secret else None
            provider = OpenAICompatibleEmbeddingProvider(
                api_url=getattr(settings, "embedding_api_url", "https://api.openai.com/v1/embeddings"),
                model_id=model_id,
                api_key=api_key,
                dimensions=expected_dimensions,
                timeout_seconds=getattr(settings, "embedding_timeout_seconds", 30),
                max_retries=getattr(settings, "embedding_max_retries", 3),
                retry_base_seconds=getattr(settings, "embedding_retry_base_seconds", 0.25),
                retry_max_seconds=getattr(settings, "embedding_retry_max_seconds", 4),
            )
        else:
            raise EmbeddingConfigurationError(f"Unsupported embedding provider: {provider_name}")
        return cls(
            provider,
            model_id=model_id,
            expected_dimensions=expected_dimensions,
            batch_size=batch_size,
        )

    async def embed_chunks(
        self,
        chunks: list[DocumentChunk],
        *,
        existing: dict[str, EmbeddedChunk] | None = None,
    ) -> list[EmbeddedChunk]:
        """Embed chunks, reusing valid unchanged embeddings in input order.

        Cached vectors are reused only when their text hash, model, and vector
        dimensions match the current service configuration. Every generated
        vector in a call must have one consistent dimensionality.
        """
        cache = existing or {}
        output: list[EmbeddedChunk | None] = [None] * len(chunks)
        pending: list[tuple[int, DocumentChunk, str]] = []
        for index, chunk in enumerate(chunks):
            content_hash = self.content_hash(chunk.text)
            cached = cache.get(chunk.chunk_id)
            if cached is not None and self._cache_is_valid(cached, content_hash):
                self._accept_dimensions(cached.embedding_dimensions)
                output[index] = cached
            else:
                pending.append((index, chunk, content_hash))

        for offset in range(0, len(pending), self.batch_size):
            batch = pending[offset : offset + self.batch_size]
            try:
                vectors = await self.provider.embed([chunk.text for _, chunk, _ in batch])
            except EmbeddingError:
                raise
            except Exception as exc:
                raise EmbeddingProviderError("Embedding provider request failed.") from exc
            if not isinstance(vectors, list) or len(vectors) != len(batch):
                raise MalformedEmbeddingResponseError(
                    "Embedding provider returned a different number of vectors than inputs."
                )
            for (index, chunk, content_hash), vector in zip(batch, vectors, strict=True):
                validated = self._validate_vector(vector)
                dimensions = len(validated)
                self._accept_dimensions(dimensions)
                output[index] = EmbeddedChunk(
                    chunk_id=chunk.chunk_id,
                    embedding=validated,
                    embedding_model=self.model_id,
                    embedding_dimensions=dimensions,
                    content_hash=content_hash,
                )
        return [record for record in output if record is not None]

    async def embed_query(self, query: str) -> list[float]:
        """Embed one query using the same provider, model, and dimension checks."""
        if not query.strip():
            raise ValueError("query must not be empty")
        try:
            vectors = await self.provider.embed([query.strip()])
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError("Embedding provider request failed.") from exc
        if not isinstance(vectors, list) or len(vectors) != 1:
            raise MalformedEmbeddingResponseError(
                "Embedding provider did not return exactly one query vector."
            )
        vector = self._validate_vector(vectors[0])
        self._accept_dimensions(len(vector))
        return vector

    @staticmethod
    def content_hash(text: str) -> str:
        """Return a stable digest used to detect unchanged chunk contents."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _cache_is_valid(self, cached: EmbeddedChunk, content_hash: str) -> bool:
        return (
            cached.content_hash == content_hash
            and cached.embedding_model == self.model_id
            and cached.embedding_dimensions == len(cached.embedding)
            and (self.expected_dimensions is None or cached.embedding_dimensions == self.expected_dimensions)
        )

    def _validate_vector(self, vector: object) -> list[float]:
        if not isinstance(vector, list) or not vector:
            raise MalformedEmbeddingResponseError("Embedding provider returned an empty or invalid vector.")
        try:
            values = [float(value) for value in vector]
        except (TypeError, ValueError, OverflowError) as exc:
            raise MalformedEmbeddingResponseError("Embedding provider returned non-numeric values.") from exc
        if any(not math.isfinite(value) for value in values):
            raise MalformedEmbeddingResponseError("Embedding provider returned non-finite values.")
        return values

    def _accept_dimensions(self, dimensions: int) -> None:
        if self.expected_dimensions is not None and dimensions != self.expected_dimensions:
            raise IncompatibleEmbeddingError(
                f"Configured embedding dimensions ({self.expected_dimensions}) do not match provider output ({dimensions})."
            )
        if self._observed_dimensions is None:
            self._observed_dimensions = dimensions
        elif dimensions != self._observed_dimensions:
            raise IncompatibleEmbeddingError(
                f"Embedding dimension changed from {self._observed_dimensions} to {dimensions}."
            )


def validate_vector_collection(records: list[EmbeddedChunk]) -> tuple[str, int] | None:
    """Reject mixed model/dimension records before writing to one vector column."""
    if not records:
        return None
    model = records[0].embedding_model
    dimensions = records[0].embedding_dimensions
    if any(record.embedding_model != model or record.embedding_dimensions != dimensions for record in records):
        raise IncompatibleEmbeddingError("A vector collection cannot mix embedding models or dimensions.")
    return model, dimensions
