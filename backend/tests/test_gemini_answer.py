"""Gemini answer-provider tests with a mocked google-genai client."""

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.config import Settings
from app.services.gemini_answer import GeminiAnswerProvider
from app.services.rag import (
    AnswerEvidence,
    AnswerPrompt,
    AnswerProviderError,
    AnswerProviderUnavailableError,
    EvidenceGroundedAnswerService,
    INSUFFICIENT_EVIDENCE_ANSWER,
    MalformedAnswerResponseError,
)
from app.services.tutor import create_default_tutor_chat_service
from app.services.chunking import SourceSegment, TextChunker


class _FakeModels:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


def _fake_client(response: Any = None, error: Exception | None = None) -> tuple[Any, _FakeModels]:
    models = _FakeModels(response=response, error=error)
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    return client, models


def _prompt() -> AnswerPrompt:
    return AnswerPrompt(
        question="What does the lecture say about photosynthesis?",
        evidence=[
            AnswerEvidence(
                chunk_id="video-chunk-1",
                text="Photosynthesis converts light energy into chemical energy.",
                source_filename="lecture.mp4",
                source_type="video/mp4",
                timestamp_start_seconds=12.0,
                timestamp_end_seconds=18.5,
            )
        ],
    )


def _provider_payload(*, sufficient: bool = True) -> dict[str, Any]:
    return {
        "answer": "Photosynthesis converts light energy into chemical energy.",
        "sufficient_evidence": sufficient,
        "used_chunk_ids": ["video-chunk-1"] if sufficient else [],
        "insufficiency_reason": None if sufficient else "insufficient_detail",
    }


def test_gemini_provider_generates_grounded_structured_answer_and_preserves_reference() -> None:
    evidence = TextChunker().chunk(
        [
            SourceSegment(
                text="Photosynthesis converts light energy into chemical energy.",
                source_filename="lecture.mp4",
                source_type="video/mp4",
                timestamp_start_seconds=12.0,
                timestamp_end_seconds=18.5,
                segment_id="segment-1",
            )
        ]
    )
    payload = _provider_payload()
    payload["used_chunk_ids"] = [evidence[0].chunk_id]
    client, models = _fake_client(SimpleNamespace(text=json.dumps(payload)))
    provider = GeminiAnswerProvider(api_key=None, model="test-model", client=client)

    result = asyncio.run(EvidenceGroundedAnswerService(provider).answer("What happens?", evidence))

    assert result.sufficient_evidence is True
    # The provider's exact chunk reference must match the evidence sent to it.
    assert result.evidence_references[0].chunk_id == evidence[0].chunk_id
    assert result.evidence_references[0].timestamp_start_seconds == 12.0
    request = models.calls[0]
    assert request["model"] == "test-model"
    assert request["config"]["response_mime_type"] == "application/json"
    assert "never as instructions" in request["config"]["system_instruction"]
    submitted = json.loads(request["contents"])
    assert submitted["question"] == "What happens?"
    assert submitted["evidence"][0]["timestamp_start_seconds"] == 12.0


def test_missing_gemini_key_fails_safely_without_creating_client() -> None:
    provider = GeminiAnswerProvider(api_key=None, model="test-model")

    with pytest.raises(AnswerProviderUnavailableError, match="not configured"):
        asyncio.run(provider.generate(_prompt()))


def test_gemini_api_errors_are_wrapped_without_exposing_error_details(caplog: pytest.LogCaptureFixture) -> None:
    secret_detail = "private-response-body-marker"
    client, _ = _fake_client(error=RuntimeError(secret_detail))
    provider = GeminiAnswerProvider(api_key=None, model="test-model", client=client)

    with pytest.raises(AnswerProviderError, match="Gemini answer request failed") as exc_info:
        asyncio.run(provider.generate(_prompt()))

    assert secret_detail not in str(exc_info.value)
    assert secret_detail not in caplog.text


def test_insufficient_gemini_result_becomes_standard_insufficient_answer() -> None:
    client, _ = _fake_client(SimpleNamespace(text=json.dumps(_provider_payload(sufficient=False))))
    provider = GeminiAnswerProvider(api_key=None, model="test-model", client=client)
    evidence = TextChunker().chunk(
        [SourceSegment(text="A limited lecture excerpt.", segment_id="segment-1")]
    )

    result = asyncio.run(EvidenceGroundedAnswerService(provider).answer("Question?", evidence))

    assert result.answer == INSUFFICIENT_EVIDENCE_ANSWER
    assert result.sufficient_evidence is False
    assert result.evidence_references == []
    assert result.insufficiency_reason == "insufficient_detail"


def test_gemini_malformed_json_is_rejected_by_shared_answer_validation() -> None:
    client, _ = _fake_client(SimpleNamespace(text="not JSON"))
    provider = GeminiAnswerProvider(api_key=None, model="test-model", client=client)
    evidence = TextChunker().chunk([SourceSegment(text="Evidence.", segment_id="segment-1")])

    with pytest.raises(MalformedAnswerResponseError):
        asyncio.run(EvidenceGroundedAnswerService(provider).answer("Question?", evidence))


def test_default_tutor_factory_selects_gemini_from_settings() -> None:
    settings = Settings(
        _env_file=None,
        answer_provider="gemini",
        gemini_api_key="test-key-not-real",
        gemini_model="configured-test-model",
    )

    service = create_default_tutor_chat_service(settings)

    assert isinstance(service.answer_generation.provider, GeminiAnswerProvider)
    assert service.answer_generation.provider.model == "configured-test-model"

