"""
Dependency injection — all heavy services are singletons.

Improvements:
- asyncio.Lock() on Qdrant init prevents TOCTOU double-init
- QueryService, SummarizationService, LiteratureService are singletons
- get_elasticsearch_client alias removed (was dead code)
- warm_up() called at startup to eliminate cold-start penalty
"""
import asyncio
from typing import Optional

from fastapi import Depends, Request
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
_qdrant_lock = asyncio.Lock()

_embedding_service: Optional[EmbeddingService] = None
_llm_service: Optional[LLMService] = None

_document_service: Optional[DocumentService] = None
_query_service: Optional[QueryService] = None
_summarization_service: Optional[SummarizationService] = None
_literature_service: Optional[LiteratureService] = None


# ── Request context ───────────────────────────────────────────────────────────

async def get_request_id(request: Request) -> str:
    import uuid
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    set_request_id(rid)
    return rid


# ── Infrastructure singletons ─────────────────────────────────────────────────

async def get_qdrant() -> QdrantVectorStore:
    global _qdrant
    if _qdrant is not None:
        return _qdrant
    async with _qdrant_lock:
        if _qdrant is None:
            try:
                from app.retrieval.qdrant_client import get_qdrant_client
                _qdrant = get_qdrant_client()
                await _qdrant.initialize()
                app_logger.info("Qdrant ready")
            except Exception as e:
                app_logger.error(f"Qdrant init failed: {e}")
                raise ServiceUnavailableError("Qdrant", detail=str(e))
    return _qdrant


async def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        from app.services.embedding_service import embedding_service
        _embedding_service = embedding_service
        app_logger.info("Embedding service ready")
    return _embedding_service


async def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
        await _llm_service.initialize()
        app_logger.info("Groq LLM service ready")
    return _llm_service


# ── Service singletons ────────────────────────────────────────────────────────

async def get_document_service(
    qdrant: QdrantVectorStore = Depends(get_qdrant),
    emb: EmbeddingService = Depends(get_embedding_service),
) -> DocumentService:
    global _document_service
    if _document_service is None:
        _document_service = DocumentService(es_client=qdrant, embedding_service=emb)
    return _document_service


async def get_query_service(
    qdrant: QdrantVectorStore = Depends(get_qdrant),
    emb: EmbeddingService = Depends(get_embedding_service),
    llm: LLMService = Depends(get_llm_service),
) -> QueryService:
    global _query_service
    if _query_service is None:
        _query_service = QueryService(es_client=qdrant, embedding_service=emb, llm_service=llm)
    return _query_service


async def get_summarization_service(
    qdrant: QdrantVectorStore = Depends(get_qdrant),
    llm: LLMService = Depends(get_llm_service),
) -> SummarizationService:
    global _summarization_service
    if _summarization_service is None:
        _summarization_service = SummarizationService(es_client=qdrant, llm_service=llm)
    return _summarization_service


async def get_literature_service(
    qdrant: QdrantVectorStore = Depends(get_qdrant),
    emb: EmbeddingService = Depends(get_embedding_service),
    llm: LLMService = Depends(get_llm_service),
) -> LiteratureService:
    global _literature_service
    if _literature_service is None:
        _literature_service = LiteratureService(
            es_client=qdrant, embedding_service=emb, llm_service=llm
        )
    return _literature_service


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    return None


# ── Startup warm-up — eliminates cold-start penalty ──────────────────────────

async def warm_up():
    """Pre-initialize all services at startup so the first request is fast."""
    app_logger.info("Warming up services...")
    try:
        qdrant = await get_qdrant()
        emb = await get_embedding_service()
        llm = await get_llm_service()
        # Force embedding model to load by running a tiny encode
        await emb.embed_query_async("warmup")
        app_logger.info("All services warmed up")
    except Exception as e:
        app_logger.warning(f"Warm-up partial failure (non-fatal): {e}")


# ── Shutdown cleanup ──────────────────────────────────────────────────────────

async def cleanup_services():
    global _qdrant, _embedding_service, _llm_service
    global _document_service, _query_service, _summarization_service, _literature_service
    if _qdrant:
        await _qdrant.close()
        _qdrant = None
    if _llm_service:
        await _llm_service.cleanup()
        _llm_service = None
    _embedding_service = None
    _document_service = None
    _query_service = None
    _summarization_service = None
    _literature_service = None
    app_logger.info("Services cleaned up")
