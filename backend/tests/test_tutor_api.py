"""API integration tests using deterministic local embedding and answer mocks."""

import asyncio

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.chunking import SourceSegment, TextChunker
from app.services.embeddings import EmbeddedChunk, EmbeddingService
from app.services.rag import (
    EvidenceGroundedAnswerService,
    INSUFFICIENT_EVIDENCE_ANSWER,
    MockAnswerProvider,
    ProviderAnswer,
)
from app.services.retrieval import RetrievalService
from app.services.tutor import TutorChatService
from app.services.vector_store import InMemoryVectorStore, IndexedChunk


class _QueryEmbeddingProvider:
    """Return a fixed vector; this is a test fixture, not semantic embedding."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def _chunks():
    return TextChunker().chunk(
        [
            SourceSegment(
                text="Cell membranes regulate transport.",
                document_id="doc-pdf",
                source_id="src-pdf",
                source_filename="cells.pdf",
                source_type="application/pdf",
                course_id="biology",
                page_number=8,
            ),
            SourceSegment(
                text="The nucleus stores genetic material.",
                document_id="doc-ppt",
                source_filename="cells.pptx",
                source_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                course_id="biology",
                slide_number=3,
            ),
            SourceSegment(
                text="The lecturer explains the cell wall.",
                document_id="doc-video",
                source_filename="cells.mp4",
                source_type="video/mp4",
                course_id="biology",
                timestamp_start_seconds=94.25,
                timestamp_end_seconds=102.5,
            ),
        ]
    )


def _service(
    response: ProviderAnswer | dict[str, object] | None,
    *,
    chunks=None,
    provider=None,
) -> tuple[TutorChatService, MockAnswerProvider | None]:
    store = InMemoryVectorStore()
    chunks = _chunks() if chunks is None else chunks
    if chunks:
        asyncio.run(
            store.upsert(
                [
                    IndexedChunk(
                        chunk=chunk,
                        vector=EmbeddedChunk(
                            chunk_id=chunk.chunk_id,
                            embedding=[1.0, 0.0],
                            embedding_model="test-model",
                            embedding_dimensions=2,
                            content_hash=EmbeddingService.content_hash(chunk.text),
                        ),
                    )
                    for chunk in chunks
                ]
            )
        )
    retrieval = RetrievalService(
        EmbeddingService(_QueryEmbeddingProvider(), model_id="test-model", expected_dimensions=2),
        store,
    )
    answer_provider = provider or MockAnswerProvider(response)
    return TutorChatService(retrieval, EvidenceGroundedAnswerService(answer_provider)), (
        answer_provider if isinstance(answer_provider, MockAnswerProvider) else None
    )


def test_chat_returns_supported_answer_and_cross_media_citations() -> None:
    chunks = _chunks()
    answer_provider = MockAnswerProvider(
        ProviderAnswer(
            answer="The materials discuss membranes, the nucleus, and the cell wall.",
            sufficient_evidence=True,
            used_chunk_ids=[chunk.chunk_id for chunk in chunks],
        )
    )
    service, _ = _service(None, provider=answer_provider)

    response = TestClient(create_app(service)).post(
        "/api/tutor/chat",
        json={"question": "Summarize the cell materials", "course_id": "biology"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith("The materials discuss")
    assert body["sufficient_evidence"] is True
    assert body["factual_correctness_status"] == "not_independently_verified"
    citations = body["evidence_references"]
    assert [(item["source_filename"], item["page_number"]) for item in citations[:1]] == [("cells.pdf", 8)]
    assert citations[1]["slide_number"] == 3
    assert (citations[2]["timestamp_start_seconds"], citations[2]["timestamp_end_seconds"]) == (94.25, 102.5)
    assert [item["chunk_id"] for item in citations] == [chunk.chunk_id for chunk in chunks]


def test_chat_returns_insufficient_result_when_answer_provider_cannot_support_question() -> None:
    service, _ = _service(
        ProviderAnswer(answer="Unsupported", sufficient_evidence=False, insufficiency_reason="irrelevant_evidence")
    )

    response = TestClient(create_app(service)).post("/api/tutor/chat", json={"question": "Question?"})

    assert response.status_code == 200
    assert response.json()["answer"] == INSUFFICIENT_EVIDENCE_ANSWER
    assert response.json()["sufficient_evidence"] is False
    assert response.json()["insufficiency_reason"] == "irrelevant_evidence"
    assert response.json()["evidence_references"] == []


def test_chat_without_index_returns_insufficient_without_provider_call() -> None:
    service, answer_provider = _service(None, chunks=[])

    response = TestClient(create_app(service)).post("/api/tutor/chat", json={"question": "Question?"})

    assert response.status_code == 200
    assert response.json()["sufficient_evidence"] is False
    assert response.json()["insufficiency_reason"] == "no_evidence"
    assert response.json()["evidence_references"] == []
    assert answer_provider is not None and answer_provider.calls == []


def test_chat_rejects_blank_question_and_invalid_context() -> None:
    client = TestClient(create_app(_service(None)[0]))

    blank = client.post("/api/tutor/chat", json={"question": "  "})
    invalid_context = client.post("/api/tutor/chat", json={"question": "Help", "course_id": "  "})

    assert blank.status_code == 422
    assert blank.json() == {"error": {"code": "validation_error", "message": "Request validation failed."}}
    assert invalid_context.status_code == 422


class _FailingProvider:
    async def generate(self, prompt):
        raise RuntimeError("sensitive provider detail")


class _MalformedProvider:
    async def generate(self, prompt):
        return {"answer": "Missing sufficiency field"}


def test_chat_maps_provider_failure_without_leaking_internal_error() -> None:
    service, _ = _service(None, provider=_FailingProvider())

    response = TestClient(create_app(service)).post("/api/tutor/chat", json={"question": "Question?"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Tutor answer generation is unavailable."
    assert "sensitive provider detail" not in response.text


def test_chat_maps_malformed_provider_response_to_gateway_error() -> None:
    service, _ = _service(None, provider=_MalformedProvider())

    response = TestClient(create_app(service)).post("/api/tutor/chat", json={"question": "Question?"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Tutor answer generation returned an invalid response."
