"""Tests for transcript chunking, vector indexing, and tutor retrieval."""

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes import documents as document_routes
from app.main import create_app
from app.services.embeddings import EmbeddingService, MockEmbeddingProvider
from app.services.rag import EvidenceGroundedAnswerService, ProviderAnswer
from app.services.retrieval import RetrievalService
from app.services.tutor import TutorChatService
from app.services.vector_store import InMemoryVectorStore
from app.services.video_processing import TranscriptionResult, TranscriptionSegment


class _AnswerFromRetrievedEvidence:
    """Test provider cites the evidence it receives, never a fabricated ID."""

    def __init__(self) -> None:
        self.received_evidence = []

    async def generate(self, prompt):
        self.received_evidence = prompt.evidence
        return ProviderAnswer(
            answer="The lecturer says cell membranes regulate transport.",
            sufficient_evidence=True,
            used_chunk_ids=[prompt.evidence[0].chunk_id],
        )


def _tutor_service(store: InMemoryVectorStore, answer_provider: _AnswerFromRetrievedEvidence) -> TutorChatService:
    """Use the same mock embedding service for transcript and query vectors."""
    embedding_service = EmbeddingService(
        MockEmbeddingProvider(8),
        model_id="test-hash-model-8d",
        expected_dimensions=8,
    )
    return TutorChatService(
        RetrievalService(embedding_service, store),
        EvidenceGroundedAnswerService(answer_provider),
    )


def test_media_upload_chunks_and_indexes_transcript_for_tutor(
    monkeypatch,
) -> None:
    """Uploaded transcript becomes retrievable with its source IDs and timestamps."""
    class StubMediaProcessor:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def process_path(
            self,
            media_path: Path,
            filename: str,
            *,
            document_id: str | None = None,
            source_id: str | None = None,
        ) -> TranscriptionResult:
            assert media_path.is_file()
            return TranscriptionResult(
                source_filename=filename,
                source_type="video/mp4",
                status="transcribed",
                duration_seconds=16.0,
                document_id=document_id,
                source_id=source_id,
                segments=[
                    TranscriptionSegment(
                        text="Cell membranes regulate transport.",
                        start_seconds=4.5,
                        end_seconds=7.25,
                        formatted_start_time="00:00:04.500",
                        formatted_end_time="00:00:07.250",
                        source_filename=filename,
                        source_type="video/mp4",
                        segment_id="transcript-1",
                    )
                ],
            )

    monkeypatch.setattr(document_routes, "LectureMediaProcessor", StubMediaProcessor)
    store = InMemoryVectorStore()
    answer_provider = _AnswerFromRetrievedEvidence()
    client = TestClient(create_app(_tutor_service(store, answer_provider)))

    upload = client.post(
        "/api/documents/upload/media",
        data={
            "document_id": "lecture-42",
            "source_id": "source-lecture-42",
            "course_id": "biology-101",
        },
        files={"file": ("lesson.mp4", b"mock media", "video/mp4")},
    )

    assert upload.status_code == 200
    upload_body = upload.json()
    # The existing media response shape remains unchanged.
    assert set(upload_body) == {"source_filename", "source_type", "status", "duration_seconds", "segments"}
    assert upload_body["segments"][0]["text"] == "Cell membranes regulate transport."
    assert asyncio.run(store.count(course_id="biology-101", document_id="lecture-42")) == 1

    chat = client.post(
        "/api/tutor/chat",
        json={
            "question": "What do cell membranes do?",
            "course_id": "biology-101",
            "document_id": "lecture-42",
        },
    )

    assert chat.status_code == 200
    response = chat.json()
    assert response["sufficient_evidence"] is True
    assert response["answer"] == "The lecturer says cell membranes regulate transport."
    citation = response["evidence_references"][0]
    assert citation["document_id"] == "lecture-42"
    assert citation["source_id"] == "source-lecture-42"
    assert citation["course_id"] == "biology-101"
    assert citation["source_filename"] == "lesson.mp4"
    assert citation["source_type"] == "video/mp4"
    assert citation["timestamp_start_seconds"] == 4.5
    assert citation["timestamp_end_seconds"] == 7.25
    assert answer_provider.received_evidence[0].text == "Cell membranes regulate transport."

