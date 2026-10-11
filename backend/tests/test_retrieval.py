"""Deterministic tests for vector retrieval and its in-memory store."""

import asyncio

import pytest

from app.services.chunking import SourceSegment, TextChunker
from app.services.embeddings import (
    EmbeddedChunk,
    EmbeddingProviderError,
    EmbeddingService,
    IncompatibleEmbeddingError,
    MockEmbeddingProvider,
)
from app.services.retrieval import (
    EmbeddingUnavailableError,
    RetrievalService,
    VectorStoreError,
)
from app.services.vector_store import (
    InMemoryVectorStore,
    IndexedChunk,
    cosine_similarity,
)


class _DeterministicQueryProvider:
    """Test provider maps queries to explicit vectors, not semantic outputs."""

    def __init__(self, vector: list[float]) -> None:
        self.vector = vector
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self.vector for _ in texts]


def _indexed(chunk, vector: list[float], model: str = "test-model") -> IndexedChunk:
    return IndexedChunk(
        chunk=chunk,
        vector=EmbeddedChunk(
            chunk_id=chunk.chunk_id,
            embedding=vector,
            embedding_model=model,
            embedding_dimensions=len(vector),
            content_hash=EmbeddingService.content_hash(chunk.text),
        ),
    )


def _sample_chunks():
    return TextChunker().chunk(
        [
            SourceSegment(
                text="A page about cell biology.",
                document_id="biology-doc",
                course_id="biology-course",
                source_filename="cells.pdf",
                source_type="application/pdf",
                page_number=4,
                segment_id="page-4",
            ),
            SourceSegment(
                text="A slide about cell structure.",
                document_id="biology-slides",
                course_id="biology-course",
                source_filename="cells.pptx",
                source_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                slide_number=6,
                segment_id="slide-6",
            ),
            SourceSegment(
                text="A video transcript about cells.",
                document_id="biology-video",
                course_id="biology-course",
                source_filename="cells.mp4",
                source_type="video/mp4",
                timestamp_start_seconds=21.5,
                timestamp_end_seconds=26.0,
                segment_id="speech-3",
            ),
        ]
    )


def test_retrieval_orders_by_cosine_and_preserves_media_metadata() -> None:
    """Cosine-ranked results retain PDF page, slide, and video timestamps."""
    chunks = _sample_chunks()
    store = InMemoryVectorStore()
    asyncio.run(
        store.upsert(
            [
                _indexed(chunks[0], [1.0, 0.0]),
                _indexed(chunks[1], [0.8, 0.6]),
                _indexed(chunks[2], [0.0, 1.0]),
            ]
        )
    )
    query_provider = _DeterministicQueryProvider([1.0, 0.0])
    service = RetrievalService(
        EmbeddingService(query_provider, model_id="test-model", expected_dimensions=2),
        store,
    )

    results = asyncio.run(service.retrieve("cell structure", limit=3))

    assert [result.chunk.chunk_id for result in results] == [
        chunks[0].chunk_id,
        chunks[1].chunk_id,
        chunks[2].chunk_id,
    ]
    assert [result.similarity for result in results] == pytest.approx([1.0, 0.8, 0.0])
    assert results[0].chunk.page_number == 4
    assert results[1].chunk.slide_number == 6
    assert (results[2].chunk.timestamp_start_seconds, results[2].chunk.timestamp_end_seconds) == (21.5, 26.0)
    assert all(result.is_mock_embedding is False for result in results)


def test_filters_apply_only_to_existing_course_and_document_fields() -> None:
    """Course and document filters narrow indexed chunks without altering metadata."""
    chunks = _sample_chunks()
    store = InMemoryVectorStore()
    asyncio.run(store.upsert([_indexed(chunk, [1.0, 0.0]) for chunk in chunks]))
    provider = _DeterministicQueryProvider([1.0, 0.0])
    service = RetrievalService(EmbeddingService(provider, model_id="test-model", expected_dimensions=2), store)

    results = asyncio.run(
        service.retrieve("cells", course_id="biology-course", document_id="biology-slides")
    )

    assert len(results) == 1
    assert results[0].chunk.document_id == "biology-slides"
    assert results[0].chunk.course_id == "biology-course"
    assert results[0].chunk.slide_number == 6


def test_empty_query_and_missing_index_return_empty_without_embedding() -> None:
    """Empty and unindexed retrievals do not call the embedding provider."""
    provider = _DeterministicQueryProvider([1.0, 0.0])
    service = RetrievalService(
        EmbeddingService(provider, model_id="test-model", expected_dimensions=2),
        InMemoryVectorStore(),
    )

    assert asyncio.run(service.retrieve("  ")) == []
    assert asyncio.run(service.retrieve("a valid question")) == []
    assert provider.calls == []


def test_document_vectors_are_not_regenerated_during_queries() -> None:
    """Retrieval embeds only the query and searches already indexed vectors."""
    chunks = _sample_chunks()
    store = InMemoryVectorStore()
    asyncio.run(store.upsert([_indexed(chunk, [1.0, 0.0]) for chunk in chunks]))
    provider = _DeterministicQueryProvider([1.0, 0.0])
    service = RetrievalService(EmbeddingService(provider, model_id="test-model", expected_dimensions=2), store)

    asyncio.run(service.retrieve("query one"))
    asyncio.run(service.retrieve("query two"))

    assert provider.calls == [["query one"], ["query two"]]
    assert asyncio.run(store.count()) == 3


def test_zero_vectors_and_dimension_mismatch_are_handled() -> None:
    """Zero vectors produce no query ranking; incompatible dimensions fail safely."""
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
    chunks = _sample_chunks()
    store = InMemoryVectorStore()
    asyncio.run(store.upsert([_indexed(chunks[0], [1.0, 0.0])]))
    assert asyncio.run(store.search([0.0, 0.0], limit=5)) == []
    with pytest.raises(IncompatibleEmbeddingError, match="dimension"):
        asyncio.run(store.search([1.0, 0.0, 0.0], limit=5))


def test_store_rejects_model_or_dimension_mixing() -> None:
    """One in-memory index cannot silently accept a second vector schema."""
    chunks = _sample_chunks()
    store = InMemoryVectorStore()
    asyncio.run(store.upsert([_indexed(chunks[0], [1.0, 0.0], model="model-a")]))
    with pytest.raises(IncompatibleEmbeddingError, match="different model"):
        asyncio.run(store.upsert([_indexed(chunks[1], [1.0, 0.0], model="model-b")]))


def test_query_embedding_model_must_match_indexed_model() -> None:
    """Same-size vectors from different embedding models are not compared."""
    chunk = _sample_chunks()[0]
    store = InMemoryVectorStore()
    asyncio.run(store.upsert([_indexed(chunk, [1.0, 0.0], model="indexed-model")]))
    service = RetrievalService(
        EmbeddingService(_DeterministicQueryProvider([1.0, 0.0]), model_id="query-model", expected_dimensions=2),
        store,
    )

    with pytest.raises(VectorStoreError, match="search failed"):
        asyncio.run(service.retrieve("query"))


def test_non_finite_query_vector_is_rejected() -> None:
    """Vector validation rejects NaN values before cosine scoring."""
    store = InMemoryVectorStore()
    with pytest.raises(ValueError, match="finite"):
        asyncio.run(store.search([float("nan"), 0.0], limit=1))


class _UnavailableProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingProviderError("offline")


def test_embedding_unavailability_is_reported_as_safe_retrieval_error() -> None:
    """Provider errors do not leak lower-level detail through retrieval."""
    chunk = _sample_chunks()[0]
    store = InMemoryVectorStore()
    asyncio.run(store.upsert([_indexed(chunk, [1.0, 0.0])]))
    service = RetrievalService(
        EmbeddingService(_UnavailableProvider(), model_id="test-model", expected_dimensions=2),
        store,
    )

    with pytest.raises(EmbeddingUnavailableError, match="unavailable") as exc_info:
        asyncio.run(service.retrieve("query"))
    assert "offline" not in str(exc_info.value)


class _FailingStore(InMemoryVectorStore):
    async def count(self, *, course_id: str | None = None, document_id: str | None = None) -> int:
        raise RuntimeError("database internals")


def test_storage_failures_are_reported_without_internal_details() -> None:
    """Storage exceptions are translated into a safe retrieval error."""
    service = RetrievalService(
        EmbeddingService(MockEmbeddingProvider(2), model_id="mock-test", expected_dimensions=2),
        _FailingStore(),
    )

    with pytest.raises(VectorStoreError, match="unavailable") as exc_info:
        asyncio.run(service.retrieve("query"))
    assert "database internals" not in str(exc_info.value)


def test_mock_retrieval_is_explicitly_marked_as_non_semantic() -> None:
    """Deterministic mock vector results are labeled rather than presented as semantic."""
    chunk = _sample_chunks()[0]
    store = InMemoryVectorStore()
    asyncio.run(store.upsert([_indexed(chunk, [1.0, 0.0], model="mock-hash-v1")]))
    service = RetrievalService(
        EmbeddingService(MockEmbeddingProvider(2), model_id="mock-hash-v1", expected_dimensions=2),
        store,
    )

    results = asyncio.run(service.retrieve("query"))

    assert results
    assert results[0].is_mock_embedding is True
