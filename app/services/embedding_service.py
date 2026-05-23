"""
Embedding service — sentence-transformers with async wrapper.
CPU-bound encode() runs in a thread pool so it never blocks the event loop.
Supports two backends: local sentence-transformers (default) or HuggingFace Inference API.
Set EMBEDDING_PROVIDER=hf_api to use the API backend (no torch required).
"""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Union

from app.core.config import settings
from app.utils.logger import app_logger

# Dedicated thread pool for CPU-bound embedding work (1 thread = no GIL contention)
_EMBED_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="embed")


class EmbeddingService:
    """Generate embeddings — sync encode wrapped in async executor."""

    _instance = None
    _model = None
    _use_local: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self.model_name = settings.embedding_model
            self.batch_size = settings.embedding_batch_size
            try:
                import torch
                from sentence_transformers import SentenceTransformer

                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                app_logger.info(f"Loading embedding model: {self.model_name} on {self.device}")
                self._model = SentenceTransformer(self.model_name)
                self._model.to(self.device)
                self._use_local = True
                app_logger.info("Embedding model loaded")
            except ImportError:
                app_logger.warning("sentence-transformers not available — no embeddings")
                self._model = None
                self._use_local = False
                self.device = "cpu"

    # ── sync encode (runs inside executor) ───────────────────────────────────

    def _encode_sync(self, texts: List[str]) -> List[List[float]]:
        """Blocking encode — always called via executor, never directly."""
        if not self._use_local or self._model is None:
            raise RuntimeError("Embedding model not loaded")
        vecs = self._model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vecs.tolist()

    # ── async public API ──────────────────────────────────────────────────────

    async def embed_texts_async(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts without blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EMBED_EXECUTOR, self._encode_sync, texts)

    async def embed_query_async(self, query: str) -> List[float]:
        """Embed a single query string (cached)."""
        results = await self.embed_texts_async([query])
        return results[0]

    async def embed_documents_async(self, docs: List[str]) -> List[List[float]]:
        """Embed a batch of document texts."""
        return await self.embed_texts_async(docs)

    # ── sync shims (kept for backward compat, avoid in hot paths) ────────────

    def embed_query(self, query: str) -> List[float]:
        return self._encode_sync([query])[0]

    def embed_documents(self, docs: List[str]) -> List[List[float]]:
        return self._encode_sync(docs)

    def embed_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        if isinstance(text, str):
            return self._encode_sync([text])[0]
        return self._encode_sync(text)

    @property
    def embedding_dimension(self) -> int:
        if self._use_local and self._model:
            return self._model.get_sentence_embedding_dimension()
        return settings.embedding_dimension


# ── Lazy singleton ────────────────────────────────────────────────────────────

class _LazyEmbeddingService:
    _real: EmbeddingService = None

    def _get(self) -> EmbeddingService:
        if self._real is None:
            self._real = EmbeddingService()
        return self._real

    def __getattr__(self, name):
        return getattr(self._get(), name)

    async def embed_query_async(self, q: str) -> List[float]:
        return await self._get().embed_query_async(q)

    async def embed_documents_async(self, docs: List[str]) -> List[List[float]]:
        return await self._get().embed_documents_async(docs)

    async def embed_texts_async(self, texts: List[str]) -> List[List[float]]:
        return await self._get().embed_texts_async(texts)

    def embed_query(self, q: str) -> List[float]:
        return self._get().embed_query(q)

    def embed_documents(self, docs: List[str]) -> List[List[float]]:
        return self._get().embed_documents(docs)

    @property
    def embedding_dimension(self) -> int:
        return self._get().embedding_dimension


embedding_service = _LazyEmbeddingService()
