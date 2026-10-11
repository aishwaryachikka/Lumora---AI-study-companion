"""Health endpoint response models."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Basic liveness response."""

    status: Literal["ok"]
