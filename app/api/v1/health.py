"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends
from datetime import datetime

from app.models.schemas import HealthResponse
from app.core.config import settings
from app.retrieval.elasticsearch_client import ElasticsearchClient
from app.services.llm_service import LLMService
from app.api.deps import get_elasticsearch_client, get_llm_service
from app.utils.logger import app_logger


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse, include_in_schema=False)
async def health_check(
    es_client: ElasticsearchClient = Depends(get_elasticsearch_client),
    llm_service: LLMService = Depends(get_llm_service),
) -> HealthResponse:
    """
    Health check endpoint to verify system status.
    
    Returns:
        HealthResponse with system status
    """
    # Check Elasticsearch connection
    es_connected = False
    try:
        es_connected = await es_client.ping()
    except Exception as e:
        app_logger.warning(f"Elasticsearch health check failed: {e}")
    
    # Check Ollama availability
    ollama_available = False
    try:
        ollama_available = await llm_service.is_available()
    except Exception as e:
        app_logger.warning(f"Ollama health check failed: {e}")
    
    # Determine overall status
    if es_connected and ollama_available:
        status = "healthy"
    elif es_connected or ollama_available:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        version=settings.app_version,
        elasticsearch_connected=es_connected,
        ollama_available=ollama_available,
        timestamp=datetime.utcnow(),
    )


@router.get("/ready")
async def readiness_check(
    es_client: ElasticsearchClient = Depends(get_elasticsearch_client),
) -> dict:
    """
    Readiness check for Kubernetes/container orchestration.
    
    Returns:
        Simple ready status
    """
    try:
        es_connected = await es_client.ping()
        if es_connected:
            return {"status": "ready"}
        else:
            return {"status": "not ready", "reason": "Elasticsearch not connected"}
    except Exception as e:
        return {"status": "not ready", "reason": str(e)}


@router.get("/live")
async def liveness_check() -> dict:
    """
    Liveness check for Kubernetes/container orchestration.
    
    Returns:
        Simple alive status
    """
    return {"status": "alive"}
