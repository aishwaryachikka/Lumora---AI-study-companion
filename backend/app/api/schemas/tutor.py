"""Request models for the tutor chat API."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TutorChatRequest(BaseModel):
    """Student question and optional filters supported by DocumentChunk."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=10_000)
    course_id: str | None = Field(default=None, max_length=200)
    document_id: str | None = Field(default=None, max_length=200)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        """Reject blank questions and avoid sending surrounding whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("question must not be blank")
        return normalized

    @field_validator("course_id", "document_id")
    @classmethod
    def normalize_filter(cls, value: str | None) -> str | None:
        """Normalize optional context filters and reject whitespace-only values."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("context filters must not be blank")
        return normalized
