"""Tutor chat endpoint with client-safe error mapping."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.schemas.tutor import TutorChatRequest
from app.services.rag import (
    AnswerProviderError,
    AnswerProviderTimeoutError,
    EmptyQuestionError,
    GroundedAnswerResponse,
    MalformedAnswerResponseError,
)
from app.services.retrieval import EmbeddingUnavailableError, VectorStoreError
from app.services.tutor import TutorChatService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tutor", tags=["tutor"])


def get_tutor_chat_service(request: Request) -> TutorChatService:
    """Resolve the app-scoped tutor services (replaceable by app factory)."""
    return request.app.state.tutor_chat_service


@router.post("/chat", response_model=GroundedAnswerResponse)
async def tutor_chat(
    payload: TutorChatRequest,
    service: TutorChatService = Depends(get_tutor_chat_service),
) -> GroundedAnswerResponse:
    """Answer from retrieved course evidence and cite only supplied chunks."""
    try:
        return await service.chat(
            payload.question,
            course_id=payload.course_id,
            document_id=payload.document_id,
        )
    except EmptyQuestionError as exc:
        raise HTTPException(status_code=422, detail="A non-empty question is required.") from exc
    except EmbeddingUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Tutor retrieval is temporarily unavailable.") from exc
    except VectorStoreError as exc:
        raise HTTPException(status_code=503, detail="Tutor retrieval is temporarily unavailable.") from exc
    except AnswerProviderTimeoutError as exc:
        raise HTTPException(status_code=504, detail="Tutor answer generation timed out.") from exc
    except MalformedAnswerResponseError as exc:
        raise HTTPException(status_code=502, detail="Tutor answer generation returned an invalid response.") from exc
    except AnswerProviderError as exc:
        raise HTTPException(status_code=503, detail="Tutor answer generation is unavailable.") from exc
    except Exception as exc:
        logger.exception("Tutor chat request failed")
        raise HTTPException(status_code=500, detail="Tutor request failed.") from exc
