"""Provider-neutral vector storage interface and in-memory implementation."""

import hashlib
import math
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.chunking import DocumentChunk
from app.services.embeddings import EmbeddedChunk, IncompatibleEmbeddingError, validate_vector_collection


class IndexedChunk(BaseModel):
    """A source-aware document chunk paired with its generated vector record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk: DocumentChunk
    vector: EmbeddedChunk

    @model_validator(mode="after")
    def matching_chunk_id(self) -> "IndexedChunk":
        """Ensure the vector row points at the chunk whose text it represents."""
        if self.chunk.chunk_id != self.vector.chunk_id:
            raise ValueError("chunk and embedding chunk_id must match")
        content_hash = hashlib.sha256(self.chunk.text.encode("utf-8")).hexdigest()
        if self.vector.content_hash != content_hash:
            raise ValueError("embedding content_hash does not match chunk text")
        return self


class ScoredChunk(BaseModel):
    """Retrieved chunk and its cosine score, with the vector model identified."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk: DocumentChunk
    similarity: float = Field(ge=-1, le=1)
    embedding_model: str = Field(min_length=1)
    embedding_dimensions: int = Field(gt=0)
    is_mock_embedding: bool = False


class VectorStore(Protocol):
    """Interface a persistent Supabase/pgvector adapter can implement later."""

    async def upsert(self, records: list[IndexedChunk]) -> None:
        """Insert or replace chunk vectors, enforcing one model/dimension set."""
        ...

    async def count(self, *, course_id: str | None = None, document_id: str | None = None) -> int:
        """Count indexed chunks matching supported metadata filters."""
        ...

    async def search(
        self,
        vector: list[float],
        *,
        limit: int,
        embedding_model: str | None = None,
        course_id: str | None = None,
        document_id: str | None = None,
    ) -> list[ScoredChunk]:
        """Search vectors and return ranked chunks with source metadata."""
        ...


class InMemoryVectorStore:
    """Process-local vector index for development and deterministic tests.

    This store is not durable or shared between workers. It uses actual cosine
    similarity on supplied vectors; mock embedding vectors are deterministic
    but not semantic, and retrieval marks their results accordingly.
    """

    def __init__(self) -> None:
        self._records: dict[str, IndexedChunk] = {}
        self._model: str | None = None
        self._dimensions: int | None = None

    async def upsert(self, records: list[IndexedChunk]) -> None:
        """Add vectors after validating model and dimensions for the index."""
        if not records:
            return
        collection = validate_vector_collection([record.vector for record in records])
        assert collection is not None
        model, dimensions = collection
        if self._model is not None and (model != self._model or dimensions != self._dimensions):
            raise IncompatibleEmbeddingError(
                "The in-memory vector index already contains a different model or dimensionality."
            )
        for record in records:
            if len(record.vector.embedding) != dimensions:
                raise IncompatibleEmbeddingError("Embedding vector length does not match collection metadata.")
        self._model = model
        self._dimensions = dimensions
        for record in records:
            self._records[record.chunk.chunk_id] = record

    async def count(self, *, course_id: str | None = None, document_id: str | None = None) -> int:
        """Count records within optional filters supported by DocumentChunk."""
        return sum(
            self._matches(record.chunk, course_id, document_id)
            for record in self._records.values()
        )

    async def search(
        self,
        vector: list[float],
        *,
        limit: int,
        embedding_model: str | None = None,
        course_id: str | None = None,
        document_id: str | None = None,
    ) -> list[ScoredChunk]:
        """Rank matching chunks by cosine similarity with deterministic ties."""
        query_vector = self._validate_vector(vector)
        if limit <= 0 or not self._records:
            return []
        if embedding_model is not None and embedding_model != self._model:
            raise IncompatibleEmbeddingError(
                "Query embedding model does not match the indexed vector model."
            )
        if self._dimensions is not None and len(query_vector) != self._dimensions:
            raise IncompatibleEmbeddingError(
                f"Query vector dimension ({len(query_vector)}) does not match index dimension ({self._dimensions})."
            )
        # A zero query has no direction and therefore cannot meaningfully rank
        # candidates. Return no results instead of inventing a ranking.
        if self._norm(query_vector) == 0:
            return []
        ranked: list[ScoredChunk] = []
        for record in self._records.values():
            if not self._matches(record.chunk, course_id, document_id):
                continue
            similarity = cosine_similarity(query_vector, record.vector.embedding)
            ranked.append(
                ScoredChunk(
                    chunk=record.chunk,
                    similarity=similarity,
                    embedding_model=record.vector.embedding_model,
                    embedding_dimensions=record.vector.embedding_dimensions,
                )
            )
        ranked.sort(key=lambda result: (-result.similarity, result.chunk.chunk_id))
        return ranked[:limit]

    @staticmethod
    def _matches(chunk: DocumentChunk, course_id: str | None, document_id: str | None) -> bool:
        return (course_id is None or chunk.course_id == course_id) and (
            document_id is None or chunk.document_id == document_id
        )

    @staticmethod
    def _validate_vector(vector: list[float]) -> list[float]:
        if not isinstance(vector, list) or not vector:
            raise ValueError("query vector must not be empty")
        try:
            values = [float(value) for value in vector]
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("query vector must contain numeric values") from exc
        if any(not math.isfinite(value) for value in values):
            raise ValueError("query vector values must be finite")
        return values

    @staticmethod
    def _norm(vector: list[float]) -> float:
        return math.sqrt(sum(value * value for value in vector))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity, defining a zero vector's score as 0.0."""
    left_values = InMemoryVectorStore._validate_vector(left)
    right_values = InMemoryVectorStore._validate_vector(right)
    if len(left_values) != len(right_values):
        raise IncompatibleEmbeddingError("Cannot compare vectors with different dimensions.")
    left_norm = InMemoryVectorStore._norm(left_values)
    right_norm = InMemoryVectorStore._norm(right_values)
    if left_norm == 0 or right_norm == 0:
        return 0.0
    score = sum(a * b for a, b in zip(left_values, right_values, strict=True)) / (left_norm * right_norm)
    # Guard against tiny floating-point excursions outside cosine's range.
    return max(-1.0, min(1.0, score))
