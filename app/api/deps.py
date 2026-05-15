"""
Dependency injection for FastAPI endpoints.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.utils.logger import app_logger, set_request_id
from app.retrieval.qdrant_client import QdrantVectorStore
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.services.query_service import QueryService
from app.services.summarization_service import SummarizationService
from app.services.literature_service import LiteratureService

security = HTTPBearer(auto_error=False)

# ── Singletons ────────────────────────────────────────────────────────────────
_qdrant: Optional[QdrantVectorStore] = None
_embedding_service: Optional[EmbeddingService] = None
_llm_service: Optional[LLMService] = None


async def get_request_id(request: Request) -> str:
    import uuid
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    set_request_id(request_id)
    return request_id


# ── Clients ───────────────────────────────────────────────────────────────────

async def get_qdrant() -> QdrantVectorStore:
    global _qdrant
    if _qdrant is None:
        try:
            from app.retrieval.qdrant_client import get_qdrant_client
            _qdrant = get_qdrant_client()
            await _qdrant.initialize()
            app_logger.info("Qdrant client ready")
        except Exception as e:
            app_logger.error(f"Qdrant init failed: {e}")
            raise ServiceUnavailableError("Qdrant", detail=str(e))
    return _qdrant


# Keep backward-compat name used by document_service and others
async def get_elasticsearch_client() -> QdrantVectorStore:
    return await get_qdrant()


# ── Services ──────────────────────────────────────────────────────────────────

async def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        try:
            from app.services.embedding_service import embedding_service
            _embedding_service = embedding_service
            app_logger.info("Embedding service ready")
        except Exception as e:
            raise ServiceUnavailableError("Embedding Service", detail=str(e))
    return _embedding_service


async def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        try:
            _llm_service = LLMService()
            await _llm_service.initialize()
            app_logger.info("Groq LLM service ready")
        except Exception as e:
            raise ServiceUnavailableError("LLM Service", detail=str(e))
    return _llm_service


async def get_document_service(
    qdrant: QdrantVectorStore = Depends(get_qdrant),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> DocumentService:
    return DocumentService(
        es_client=qdrant,
        embedding_service=embedding_service,
    )


async def get_query_service(
    qdrant: QdrantVectorStore = Depends(get_qdrant),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> QueryService:
    return QueryService(
        es_client=qdrant,
        embedding_service=embedding_service,
        llm_service=llm_service,
    )


async def get_summarization_service(
    qdrant: QdrantVectorStore = Depends(get_qdrant),
    llm_service: LLMService = Depends(get_llm_service),
) -> SummarizationService:
    return SummarizationService(
        es_client=qdrant,
        llm_service=llm_service,
    )


async def get_literature_service(
    qdrant: QdrantVectorStore = Depends(get_qdrant),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> LiteratureService:
    return LiteratureService(
        es_client=qdrant,
        embedding_service=embedding_service,
        llm_service=llm_service,
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    return None


async def cleanup_services():
    global _qdrant, _embedding_service, _llm_service
    if _qdrant:
        await _qdrant.close()
        _qdrant = None
    if _llm_service:
        await _llm_service.cleanup()
        _llm_service = None
    _embedding_service = None
    app_logger.info("Services cleaned up")
