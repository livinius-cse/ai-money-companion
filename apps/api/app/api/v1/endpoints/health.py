from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    project: str
    version: str


@router.get("/health", response_model=HealthResponse)
def check_health():
    """Health check endpoint for local readiness probe."""
    return HealthResponse(
        status="healthy",
        project="AI Money Companion",
        version="1.0.0",
    )
