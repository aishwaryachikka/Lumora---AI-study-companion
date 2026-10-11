"""Service health route."""

from fastapi import APIRouter

from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Report that the API process is responding."""
    return HealthResponse(status="ok")
