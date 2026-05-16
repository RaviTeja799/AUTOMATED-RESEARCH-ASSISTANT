"""
Query service — RAG pipeline with async embedding and result caching.

Improvements:
- embed_query_async() — non-blocking embedding
- TTL cache on (question, top_k, filters) — repeated queries skip Qdrant + Groq
- Single-pass confidence assessment
- Fixed: ollama_max_tokens → groq_max_tokens
"""
import asyncio
import hashlib
import json
import time
from typing import List, Dict, Any, Optional

from app.models.schemas import QueryRequest, QueryResponse, Citation
from app.retrieval.hybrid_retriever import HybridRetriever
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.prompts.rag_prompts import RAGPrompts
from app.core.config import settings
from app.core.exceptions import RetrievalError, LLMError
from app.utils.logger import app_logger

# Simple in-process TTL cache: {cache_key: (result, expires_at)}
_QUERY_CACHE: Dict[str, tuple] = {}
_CACHE_TTL = 120  # seconds


def _cache_key(question: str, top_k: int, filters: Any) -> str:
    raw = json.dumps({"q": question, "k": top_k, "f": filters}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(key: str) -> Optional[QueryResponse]:
    entry = _QUERY_CACHE.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    _QUERY_CACHE.pop(key, None)
    return None


def _cache_set(key: str, value: QueryResponse):
    _QUERY_CACHE[key] = (value, time.time() + _CACHE_TTL)


class QueryService:
    """RAG-based query processing with citation-awareness."""

    def __init__(self, es_client, embedding_service: EmbeddingService, llm_service: LLMService):
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.retriever = HybridRetriever(
            embedding_service=embedding_service,
            semantic_weight=settings.hybrid_search_weight,
        )
        app_logger.info("QueryService initialized")

    async def query(self, request: QueryRequest) -> QueryResponse:
        start = time.time()

        # Check cache first
        key = _cache_key(request.question, request.top_k, request.filters)
        cached = _cache_get(key)
        if cached:
            app_logger.info(f"Cache hit for query: {request.question[:60]}")
            return cached

        try:
            # 1. Retrieve (async embedding inside)
            chunks = await self._retrieve_chunks(request)
            if not chunks:
                return self._no_results(request, start)

            # 2. Build prompt
            prompt = RAGPrompts.build_rag_prompt(
                question=request.question,
                context_chunks=chunks,
                include_confidence=True,
            )

            # 3. Generate answer
            answer = await self.llm_service.generate(
                prompt=prompt,
                system_prompt=RAGPrompts.SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=settings.groq_max_tokens,
            )

            # 4–6. Citations, confidence, clean (all sync, fast)
            clean = self._clean_answer(answer)
            citations = self._extract_citations(clean, chunks) if request.include_citations else []
            confidence = self._assess_confidence(clean, chunks)

            result = QueryResponse(
                answer=clean,
                citations=citations,
                confidence=confidence,
                processing_time=time.time() - start,
                retrieved_chunks=len(chunks),
            )

            _cache_set(key, result)
            return result

        except (RetrievalError, LLMError):
            raise
        except Exception as e:
            app_logger.error(f"Query error: {e}", exc_info=True)
            raise LLMError("Failed to process query", detail=str(e))

    async def _retrieve_chunks(self, request: QueryRequest) -> List[Dict[str, Any]]:
        try:
            return await self.retriever.retrieve(
                query=request.question,
                top_k=request.top_k,
                filters=request.filters,
                boost_key_sections=self._should_boost(request.question),
                min_score=settings.min_similarity_score,
            )
        except Exception as e:
            raise RetrievalError("Failed to retrieve chunks", detail=str(e))

    def _extract_citations(self, answer: str, chunks: List[Dict]) -> List[Citation]:
        citations = []
        seen = set()
        answer_lower = answer.lower()
        for chunk in chunks:
            meta = chunk.get("paper_metadata", {})
            pid = chunk.get("paper_id", "")
            if pid in seen:
                continue
            title = meta.get("title", "Unknown Paper")
            authors = meta.get("authors", [])
            if title.lower() in answer_lower or any(a.lower() in answer_lower for a in authors):
                snippet = chunk.get("text", "")[:200]
                citations.append(Citation(
                    paper_id=pid,
                    paper_title=title,
                    authors=authors,
                    chunk_id=chunk.get("chunk_id", ""),
                    page_number=chunk.get("page_number"),
                    relevance_score=chunk.get("score", 0.0),
                    text_snippet=snippet + ("..." if len(chunk.get("text", "")) > 200 else ""),
                ))
                seen.add(pid)
        return citations

    def _assess_confidence(self, answer: str, chunks: List[Dict]) -> float:
        """Single-pass confidence scoring."""
        a = answer.lower()
        no_info = any(p in a for p in (
            "don't have information", "not in the provided", "cannot find",
            "insufficient information", "not mentioned",
        ))
        if no_info:
            return 0.3

        uncertainty = sum(1 for p in (
            "may", "might", "possibly", "perhaps", "suggests", "appears", "seems",
        ) if p in a)

        citation_count = answer.count("[")
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks) if chunks else 0

        return round(
            min(citation_count / 5, 1.0) * 0.4
            + max(0.0, 1.0 - uncertainty * 0.2) * 0.3
            + min(avg_score / 10, 1.0) * 0.3,
            2,
        )

    def _clean_answer(self, answer: str) -> str:
        for marker in ("CONFIDENCE ASSESSMENT:", "Confidence Level:", "Confidence:", "VERIFICATION:"):
            if marker in answer:
                return answer.split(marker)[0].strip()
        return answer

    def _should_boost(self, question: str) -> bool:
        q = question.lower()
        return any(k in q for k in ("what is", "overview", "summary", "main", "key", "explain"))

    def _no_results(self, request: QueryRequest, start: float) -> QueryResponse:
        return QueryResponse(
            answer=(
                "I don't have any relevant information in the indexed papers to answer this question.\n"
                "1. No papers in the database discuss this topic\n"
                "2. Try rephrasing or using different keywords"
            ),
            citations=[],
            confidence=0.0,
            processing_time=time.time() - start,
            retrieved_chunks=0,
        )
