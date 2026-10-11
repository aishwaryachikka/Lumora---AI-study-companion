"""Google Gemini implementation of the existing grounded answer provider."""

import asyncio
import json
import logging
from typing import Any

from app.core.config import Settings
from app.services.rag import (
    AnswerPrompt,
    AnswerProviderError,
    AnswerProviderTimeoutError,
    AnswerProviderUnavailableError,
    ProviderAnswer,
)

logger = logging.getLogger(__name__)

_OUTPUT_INSTRUCTIONS = """
Return exactly one JSON object with these fields:
{
  "answer": "string",
  "sufficient_evidence": true,
  "used_chunk_ids": ["exact supplied chunk IDs"],
  "insufficiency_reason": null
}
For insufficient evidence, set sufficient_evidence to false, used_chunk_ids to [],
and insufficiency_reason to one of: no_evidence, irrelevant_evidence, weak_evidence,
conflicting_evidence, insufficient_detail, untraceable_answer,
provider_assessed_insufficient. Never include citations or source locations in answer
text unless those facts are directly supported by evidence. Do not add markdown fences.
""".strip()


def _safe_status_code(error: Exception) -> int | str:
    """Return an HTTP-like numeric status without logging provider error text."""
    code = getattr(error, "code", None)
    if isinstance(code, int):
        return code
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code if isinstance(status_code, int) else "unknown"


class GeminiAnswerProvider:
    """Call Gemini through the official SDK and return validated-answer input.

    The provider only returns model output. Evidence references and final response
    validation remain the responsibility of ``EvidenceGroundedAnswerService``.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        timeout_seconds: float = 60,
        client: Any | None = None,
    ) -> None:
        if not model.strip() or timeout_seconds <= 0:
            raise ValueError("Gemini model and a positive timeout are required.")
        self._api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._owns_client = client is None

    @classmethod
    def from_settings(cls, settings: Settings) -> "GeminiAnswerProvider":
        """Create a provider from validated settings without exposing credentials."""
        secret = settings.gemini_api_key
        api_key = secret.get_secret_value() if secret else None
        return cls(
            api_key=api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.gemini_timeout_seconds,
        )

    async def generate(self, prompt: AnswerPrompt) -> ProviderAnswer | dict[str, Any]:
        """Ask Gemini for a structured answer grounded only in supplied evidence."""
        if self._client is None:
            if not self._api_key:
                raise AnswerProviderUnavailableError("Gemini API key is not configured.")
            try:
                from google import genai

                self._client = genai.Client(api_key=self._api_key)
            except Exception as exc:
                logger.warning(
                    "Gemini client initialization failed error_type=%s status_code=%s",
                    type(exc).__name__,
                    _safe_status_code(exc),
                )
                raise AnswerProviderError("Gemini client initialization failed.") from exc

        request_content = json.dumps(
            {
                "question": prompt.question,
                "evidence": [item.model_dump(mode="json", exclude_none=True) for item in prompt.evidence],
            },
            ensure_ascii=False,
        )
        system_instruction = f"{prompt.system_instructions}\n\n{_OUTPUT_INSTRUCTIONS}"
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self.model,
                    contents=request_content,
                    config={
                        "system_instruction": system_instruction,
                        "response_mime_type": "application/json",
                        "temperature": 0,
                    },
                ),
                timeout=self.timeout_seconds,
            )
        except (TimeoutError, asyncio.TimeoutError) as exc:
            raise AnswerProviderTimeoutError("Gemini answer request timed out.") from exc
        except Exception as exc:
            logger.warning(
                "Gemini request failed error_type=%s status_code=%s",
                type(exc).__name__,
                _safe_status_code(exc),
            )
            raise AnswerProviderError("Gemini answer request failed.") from exc

        response_text = getattr(response, "text", None)
        if not isinstance(response_text, str):
            return {}
        try:
            parsed = json.loads(response_text)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            # Let the shared answer service classify this as a malformed response.
            return {}

    async def aclose(self) -> None:
        """Close SDK transports owned by this provider, if they were created."""
        if not self._owns_client or self._client is None:
            return
        async_client = getattr(self._client, "aio", None)
        async_close = getattr(async_client, "aclose", None)
        if callable(async_close):
            await async_close()
        sync_close = getattr(self._client, "close", None)
        if callable(sync_close):
            sync_close()
