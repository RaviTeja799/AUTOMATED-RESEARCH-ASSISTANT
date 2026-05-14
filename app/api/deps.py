"""
Dependency injection for FastAPI endpoints.
Provides reusable dependencies for services, clients, and utilities.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.utils.logger import app_logger, set_request_id
from app.retrieval.elasticsearch_client import ElasticsearchClient
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.services.query_service import QueryService
from app.services.summarization_service import SummarizationService
from app.services.literature_service import LiteratureService


# Security
security = HTTPBearer(auto_error=False)


# ============================================================================
# Request Context
# ============================================================================

async def get_request_id(request: Request) -> str:
    """Extract or generate request ID for tracking."""
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        import uuid
        request_id = str(uuid.uuid4())[:8]
    set_request_id(request_id)
    return request_id


# ============================================================================
# Singleton Instances
# ============================================================================

_es_client: Optional[ElasticsearchClient] = None
_embedding_service: Optional[EmbeddingService] = None
_llm_service: Optional[LLMService] = None


# ============================================================================
# Client Dependencies
# ============================================================================

async def get_elasticsearch_client() -> ElasticsearchClient:
    """
    Get Elasticsearch client instance (singleton).
    Uses the global instance from elasticsearch_client module.
    """
    global _es_client

    if _es_client is None:
        try:
            from app.retrieval.elasticsearch_client import es_client
            _es_client = es_client
            await _es_client.initialize()
            app_logger.info("Elasticsearch client ready")
        except Exception as e:
            app_logger.error(f"Failed to initialize Elasticsearch client: {e}")
            raise ServiceUnavailableError("Elasticsearch", detail=str(e))

    return _es_client


# ============================================================================
# Service Dependencies
# ============================================================================

async def get_embedding_service() -> EmbeddingService:
    """
    Get embedding service instance (singleton).
    Uses the global instance from embedding_service module.
    """
    global _embedding_service

    if _embedding_service is None:
        try:
            from app.services.embedding_service import embedding_service
            _embedding_service = embedding_service
            app_logger.info(f"Embedding service ready: {settings.embedding_model}")
        except Exception as e:
            app_logger.error(f"Failed to initialize embedding service: {e}")
            raise ServiceUnavailableError("Embedding Service", detail=str(e))

    return _embedding_service


async def get_llm_service() -> LLMService:
    """
    Get LLM service instance (singleton).
    """
    global _llm_service

    if _llm_service is None:
        try:
            _llm_service = LLMService()
            await _llm_service.initialize()
            app_logger.info(f"LLM service ready: {settings.ollama_model}")
        except Exception as e:
            app_logger.error(f"Failed to initialize LLM service: {e}")
            raise ServiceUnavailableError("LLM Service", detail=str(e))

    return _llm_service


async def get_document_service(
    es_client: ElasticsearchClient = Depends(get_elasticsearch_client),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> DocumentService:
    """Get document service instance."""
    return DocumentService(
        es_client=es_client,
        embedding_service=embedding_service,
    )


async def get_query_service(
    es_client: ElasticsearchClient = Depends(get_elasticsearch_client),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> QueryService:
    """Get query service instance."""
    return QueryService(
        es_client=es_client,
        embedding_service=embedding_service,
        llm_service=llm_service,
    )


async def get_summarization_service(
    es_client: ElasticsearchClient = Depends(get_elasticsearch_client),
    llm_service: LLMService = Depends(get_llm_service),
) -> SummarizationService:
    """Get summarization service instance."""
    return SummarizationService(
        es_client=es_client,
        llm_service=llm_service,
    )


async def get_literature_service(
    es_client: ElasticsearchClient = Depends(get_elasticsearch_client),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> LiteratureService:
    """Get literature review service instance."""
    return LiteratureService(
        es_client=es_client,
        embedding_service=embedding_service,
        llm_service=llm_service,
    )


# ============================================================================
# Authentication (placeholder for future use)
# ============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """Get current authenticated user (placeholder)."""
    return None


# ============================================================================
# Cleanup
# ============================================================================

async def cleanup_services():
    """Cleanup all service instances on shutdown."""
    global _es_client, _embedding_service, _llm_service

    app_logger.info("Cleaning up services...")

    if _es_client:
        await _es_client.close()
        _es_client = None

    if _llm_service:
        await _llm_service.cleanup()
        _llm_service = None

    _embedding_service = None

    app_logger.info("Services cleaned up")
