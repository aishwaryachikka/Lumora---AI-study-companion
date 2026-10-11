"""Tests for configurable and validated chunk embedding generation."""

import asyncio

import httpx
import pytest

from app.services.chunking import SourceSegment, TextChunker
from app.services.embeddings import (
    EmbeddedChunk,
    EmbeddingProviderError,
    EmbeddingService,
    IncompatibleEmbeddingError,
    MalformedEmbeddingResponseError,
    MockEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    validate_vector_collection,
)


def _chunks(count: int = 1):
    return TextChunker(chunk_size=100, overlap=0).chunk(
        [SourceSegment(text=f"Study excerpt {index}.", segment_id=f"segment-{index}") for index in range(count)]
    )


def test_embeddings_are_generated_with_model_and_dimension_metadata() -> None:
    """Successful embedding returns vectors with matching metadata."""
    provider = MockEmbeddingProvider(dimensions=4)
    service = EmbeddingService(provider, model_id="mock-v1", expected_dimensions=4)

    results = asyncio.run(service.embed_chunks(_chunks(2)))

    assert len(results) == 2
    assert all(result.embedding_model == "mock-v1" for result in results)
    assert all(result.embedding_dimensions == len(result.embedding) == 4 for result in results)
    assert all(len(result.content_hash) == 64 for result in results)
    assert validate_vector_collection(results) == ("mock-v1", 4)


def test_embedding_requests_are_split_into_configured_batches() -> None:
    """Provider calls respect batch size and return outputs in original order."""
    provider = MockEmbeddingProvider(dimensions=3)
    service = EmbeddingService(provider, model_id="mock-v1", expected_dimensions=3, batch_size=2)

    results = asyncio.run(service.embed_chunks(_chunks(5)))

    assert [len(batch) for batch in provider.calls] == [2, 2, 1]
    assert [result.chunk_id for result in results] == [chunk.chunk_id for chunk in _chunks(5)]


def test_unchanged_valid_embedding_is_reused_without_provider_call() -> None:
    """Matching content hash, model, and dimensionality avoid regeneration."""
    provider = MockEmbeddingProvider(dimensions=4)
    service = EmbeddingService(provider, model_id="mock-v1", expected_dimensions=4)
    chunks = _chunks()
    original = asyncio.run(service.embed_chunks(chunks))
    provider.calls.clear()

    reused = asyncio.run(service.embed_chunks(chunks, existing={chunks[0].chunk_id: original[0]}))

    assert reused == original
    assert provider.calls == []


def test_invalid_cached_model_is_regenerated_as_configured_model() -> None:
    """A stale model vector is not returned alongside current-model vectors."""
    chunk = _chunks()[0]
    stale = EmbeddedChunk(
        chunk_id=chunk.chunk_id,
        embedding=[1.0, 0.0],
        embedding_model="old-model",
        embedding_dimensions=2,
        content_hash=EmbeddingService.content_hash(chunk.text),
    )
    provider = MockEmbeddingProvider(dimensions=4)
    service = EmbeddingService(provider, model_id="new-model", expected_dimensions=4)

    result = asyncio.run(service.embed_chunks([chunk], existing={chunk.chunk_id: stale}))[0]

    assert result.embedding_model == "new-model"
    assert result.embedding_dimensions == 4
    assert len(provider.calls) == 1


class _FailingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("provider unavailable")


def test_provider_failure_is_reported_without_leaking_provider_details() -> None:
    """Provider failures become a stable service error."""
    service = EmbeddingService(_FailingProvider(), model_id="provider-model", expected_dimensions=2)

    with pytest.raises(EmbeddingProviderError, match="request failed") as exc_info:
        asyncio.run(service.embed_chunks(_chunks()))

    assert "provider unavailable" not in str(exc_info.value)


class _MalformedProvider:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return self.vectors


@pytest.mark.parametrize(
    "vectors",
    [[], [[]], [[float("nan"), 1.0]], [[1.0, 2.0], [3.0]]],
)
def test_malformed_or_incompatible_provider_vectors_are_rejected(vectors: list[list[float]]) -> None:
    """Missing, empty, non-finite, and mixed-dimension results are rejected."""
    service = EmbeddingService(_MalformedProvider(vectors), model_id="model-v1")

    with pytest.raises((MalformedEmbeddingResponseError, IncompatibleEmbeddingError)):
        asyncio.run(service.embed_chunks(_chunks(2) if len(vectors) == 2 else _chunks()))


def test_mixed_model_or_dimension_records_cannot_share_a_vector_collection() -> None:
    """Collection metadata validation rejects incompatible vector rows."""
    a = EmbeddedChunk(
        chunk_id="a", embedding=[1.0, 0.0], embedding_model="model-a", embedding_dimensions=2, content_hash="a"
    )
    b = EmbeddedChunk(
        chunk_id="b", embedding=[1.0, 0.0], embedding_model="model-b", embedding_dimensions=2, content_hash="b"
    )

    with pytest.raises(IncompatibleEmbeddingError, match="cannot mix"):
        validate_vector_collection([a, b])


def test_openai_compatible_provider_retries_rate_limits_with_a_bound() -> None:
    """A 429 response is retried, then the returned batch is parsed in order."""
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        assert request.headers["Authorization"] == "Bearer local-test-key"
        assert request.read()
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            },
        )

    provider = OpenAICompatibleEmbeddingProvider(
        api_url="https://embedding.example/v1/embeddings",
        model_id="compatible-model",
        api_key="local-test-key",
        max_retries=2,
        retry_base_seconds=0,
        retry_max_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    vectors = asyncio.run(provider.embed(["first", "second"]))

    assert calls == 2
    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
