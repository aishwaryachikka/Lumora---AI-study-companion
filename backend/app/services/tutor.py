"""Tutor orchestration over the existing retrieval and grounded-answer services."""

from app.core.config import Settings, get_settings
from app.services.chunking import DocumentChunk, TextChunker
from app.services.embeddings import EmbeddingService
from app.services.gemini_answer import GeminiAnswerProvider
from app.services.rag import (
    AnswerPrompt,
    AnswerProvider,
    AnswerProviderUnavailableError,
    EvidenceGroundedAnswerService,
    GroundedAnswerResponse,
    ProviderAnswer,
)
from app.services.retrieval import RetrievalService
from app.services.vector_store import InMemoryVectorStore, IndexedChunk, ScoredChunk, VectorStore


class TutorIndexingError(Exception):
    """Transcript chunks could not be embedded or written to the vector store."""


class UnconfiguredAnswerProvider:
    """Provider placeholder that fails clearly until an LLM is configured."""

    async def generate(self, prompt: AnswerPrompt) -> ProviderAnswer:
        """Signal configuration absence without exposing provider credentials."""
        del prompt
        raise AnswerProviderUnavailableError("No answer provider is configured.")


class TutorChatService:
    """Retrieve contextual evidence and pass it to the grounded-answer service."""

    def __init__(
        self,
        retrieval: RetrievalService,
        answer_generation: EvidenceGroundedAnswerService,
        *,
        retrieval_limit: int = 5,
    ) -> None:
        if retrieval_limit < 1 or retrieval_limit > 50:
            raise ValueError("retrieval_limit must be between 1 and 50")
        self.retrieval = retrieval
        self.answer_generation = answer_generation
        self.retrieval_limit = retrieval_limit

    async def chat(
        self,
        question: str,
        *,
        course_id: str | None = None,
        document_id: str | None = None,
    ) -> GroundedAnswerResponse:
        """Retrieve filtered chunks and return citations validated by RAG."""
        evidence: list[ScoredChunk] = await self.retrieval.retrieve(
            question,
            limit=self.retrieval_limit,
            course_id=course_id,
            document_id=document_id,
        )
        return await self.answer_generation.answer(question, evidence)

    async def index_segments(
        self,
        segments: list[object],
        *,
        course_id: str | None = None,
    ) -> list[DocumentChunk]:
        """Chunk and index extracted segments using this service's retrieval store.

        Segment source IDs and locations are preserved by the shared chunker.
        A course ID is attached only when the caller supplies one.
        """
        chunks = TextChunker.from_settings().chunk(segments, course_id=course_id)
        if not chunks:
            return []
        try:
            vectors = await self.retrieval.embeddings.embed_chunks(chunks)
            records = [
                IndexedChunk(chunk=chunk, vector=vector)
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            await self.retrieval.vector_store.upsert(records)
        except Exception as exc:
            raise TutorIndexingError("Extracted content could not be indexed.") from exc
        return chunks


def create_default_tutor_chat_service(
    settings: Settings | None = None,
    *,
    vector_store: VectorStore | None = None,
    answer_provider: AnswerProvider | None = None,
) -> TutorChatService:
    """Build the app's ephemeral default services, with an explicit LLM stub.

    The default vector store starts empty and is process-local. The answer
    provider is selected from settings; callers can still inject a provider
    for tests or custom deployments.
    """
    configured = settings or get_settings()
    retrieval = RetrievalService(
        EmbeddingService.from_settings(configured),
        vector_store if vector_store is not None else InMemoryVectorStore(),
    )
    if answer_provider is not None:
        configured_answer_provider = answer_provider
    elif configured.answer_provider == "gemini":
        configured_answer_provider = GeminiAnswerProvider.from_settings(configured)
    elif configured.answer_provider == "mock":
        from app.services.rag import MockAnswerProvider

        configured_answer_provider = MockAnswerProvider()
    else:
        configured_answer_provider = UnconfiguredAnswerProvider()
    answer_service = EvidenceGroundedAnswerService(configured_answer_provider)
    return TutorChatService(retrieval, answer_service)
