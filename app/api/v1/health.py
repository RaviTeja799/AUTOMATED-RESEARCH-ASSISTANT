"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends
from datetime import datetime

from app.models.schemas import HealthResponse
from app.core.config import settings
from app.retrieval.qdrant_client import QdrantVectorStore
from app.services.llm_service import LLMService
from app.api.deps import get_qdrant, get_llm_service
from app.utils.logger import app_logger

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse, include_in_schema=False)
async def health_check(
    qdrant: QdrantVectorStore = Depends(get_qdrant),
    llm_service: LLMService = Depends(get_llm_service),
) -> HealthResponse:
    """Full health check — verifies Qdrant and Groq connectivity."""
    qdrant_ok = False
    groq_ok = False

    try:
        qdrant_ok = await qdrant.ping()
    except Exception as e:
        app_logger.warning(f"Qdrant health check failed: {e}")

    try:
        groq_ok = await llm_service.is_available()
    except Exception as e:
        app_logger.warning(f"Groq health check failed: {e}")

    if qdrant_ok and groq_ok:
        overall = "healthy"
    elif qdrant_ok or groq_ok:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        qdrant_connected=qdrant_ok,
        groq_available=groq_ok,
        timestamp=datetime.utcnow(),
    )


@router.get("/ready")
async def readiness_check(
    qdrant: QdrantVectorStore = Depends(get_qdrant),
) -> dict:
    try:
        ok = await qdrant.ping()
        return {"status": "ready"} if ok else {"status": "not ready", "reason": "Qdrant unreachable"}
    except Exception as e:
        return {"status": "not ready", "reason": str(e)}


@router.get("/live")
async def liveness_check() -> dict:
    return {"status": "alive"}
