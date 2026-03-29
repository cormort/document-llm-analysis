"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Return API health status."""
    return {"status": "healthy", "service": "document-llm-analysis-api"}
