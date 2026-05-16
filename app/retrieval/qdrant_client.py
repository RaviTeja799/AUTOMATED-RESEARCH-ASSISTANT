"""
Qdrant Cloud vector store client — optimized.

Fixes vs original:
- _build_filter: list values now use MatchAny (OR) not multiple must (AND)
- get_paper_ids: in-memory cache, no full collection scroll on every call
- index_chunks: updates paper ID cache at write time
- delete_paper: removes from paper ID cache
"""
import asyncio
from typing import List, Dict, Any, Optional, Set
from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    PayloadSchemaType,
)

from app.core.config import settings
from app.models.schemas import DocumentChunk
from app.utils.logger import app_logger


class QdrantVectorStore:
    """Async Qdrant Cloud client — vector search + metadata storage."""

    def __init__(self):
        self.url = settings.qdrant_url
        self.api_key = settings.qdrant_api_key
        self.collection = settings.qdrant_collection
        self.dimension = settings.embedding_dimension
        self.client: Optional[AsyncQdrantClient] = None
        # In-memory paper ID cache — avoids full collection scroll
        self._paper_ids: Set[str] = set()
        self._paper_ids_loaded: bool = False
        self._init_lock = asyncio.Lock()
        app_logger.info(f"QdrantVectorStore configured: {self.url}")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def initialize(self):
        async with self._init_lock:
            if self.client is not None:
                return
            try:
                self.client = AsyncQdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=30,
                )
                await self._ensure_collection()
                app_logger.info(f"Qdrant connected. Collection: {self.collection}")
            except Exception as e:
                app_logger.error(f"Qdrant initialization failed: {e}")
                raise

    async def _ensure_collection(self):
        collections = await self.client.get_collections()
        names = [c.name for c in collections.collections]
        if self.collection not in names:
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
            )
            for field in ("paper_id", "section", "chunk_id"):
                await self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            app_logger.info(f"Created Qdrant collection: {self.collection}")
        else:
            app_logger.info(f"Qdrant collection exists: {self.collection}")

    async def ping(self) -> bool:
        try:
            await self.client.get_collections()
            return True
        except Exception as e:
            app_logger.error(f"Qdrant ping failed: {e}")
            return False

    async def close(self):
        if self.client:
            await self.client.close()
            app_logger.info("Qdrant client closed")

    # ── Write ─────────────────────────────────────────────────────────────────

    async def index_chunks(
        self,
        chunks: List[DocumentChunk],
        paper_metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        if not chunks:
            return 0

        points = []
        paper_id_seen = set()
        for chunk in chunks:
            if not chunk.embedding:
                continue
            payload = {
                "chunk_id": chunk.chunk_id,
                "paper_id": chunk.paper_id,
                "text": chunk.text,
                "section": chunk.section or "unknown",
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "metadata": chunk.metadata or {},
                "paper_metadata": paper_metadata or {},
            }
            points.append(PointStruct(id=str(uuid4()), vector=chunk.embedding, payload=payload))
            paper_id_seen.add(chunk.paper_id)

        if not points:
            return 0

        # Batch upsert
        batch_size = 100
        total = 0
        for i in range(0, len(points), batch_size):
            await self.client.upsert(
                collection_name=self.collection,
                points=points[i : i + batch_size],
            )
            total += len(points[i : i + batch_size])

        # Update in-memory cache
        self._paper_ids.update(paper_id_seen)
        self._paper_ids_loaded = True

        app_logger.info(f"Indexed {total} chunks to Qdrant")
        return total

    async def delete_paper(self, paper_id: str) -> int:
        await self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
            ),
        )
        self._paper_ids.discard(paper_id)
        app_logger.info(f"Deleted paper {paper_id} from Qdrant")
        return 1

    # ── Read ──────────────────────────────────────────────────────────────────

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        qdrant_filter = self._build_filter(filters) if filters else None
        results = await self.client.query_points(
            collection_name=self.collection,
            query=query_embedding,
            limit=top_k,
            query_filter=qdrant_filter,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [self._hit_to_dict(hit) for hit in results.points]

    async def get_paper_chunks(self, paper_id: str) -> List[Dict[str, Any]]:
        results, _ = await self.client.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
            ),
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )
        chunks = [self._point_to_dict(p) for p in results]
        return sorted(chunks, key=lambda x: x.get("chunk_index", 0))

    async def get_paper_ids(self) -> List[str]:
        """Return unique paper IDs — uses in-memory cache after first load."""
        if self._paper_ids_loaded:
            return list(self._paper_ids)

        # First call: scroll collection once to populate cache
        paper_ids: Set[str] = set()
        offset = None
        while True:
            results, next_offset = await self.client.scroll(
                collection_name=self.collection,
                limit=1000,
                offset=offset,
                with_payload=["paper_id"],
                with_vectors=False,
            )
            for point in results:
                pid = (point.payload or {}).get("paper_id")
                if pid:
                    paper_ids.add(pid)
            if next_offset is None:
                break
            offset = next_offset

        self._paper_ids = paper_ids
        self._paper_ids_loaded = True
        return list(self._paper_ids)

    async def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single chunk by its chunk_id payload field."""
        results, _ = await self.client.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="chunk_id", match=MatchValue(value=chunk_id))]
            ),
            limit=1,
            with_payload=True,
            with_vectors=True,
        )
        if not results:
            return None
        payload = results[0].payload or {}
        payload["embedding"] = results[0].vector
        return payload

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _hit_to_dict(self, hit) -> Dict[str, Any]:
        payload = hit.payload or {}
        return {
            "chunk_id": payload.get("chunk_id", ""),
            "paper_id": payload.get("paper_id", ""),
            "text": payload.get("text", ""),
            "section": payload.get("section"),
            "page_number": payload.get("page_number"),
            "chunk_index": payload.get("chunk_index", 0),
            "paper_metadata": payload.get("paper_metadata", {}),
            "metadata": payload.get("metadata", {}),
            "score": hit.score,
        }

    def _point_to_dict(self, point) -> Dict[str, Any]:
        payload = point.payload or {}
        return {
            "chunk_id": payload.get("chunk_id", ""),
            "paper_id": payload.get("paper_id", ""),
            "text": payload.get("text", ""),
            "section": payload.get("section"),
            "page_number": payload.get("page_number"),
            "chunk_index": payload.get("chunk_index", 0),
            "paper_metadata": payload.get("paper_metadata", {}),
        }

    def _build_filter(self, filters: Dict[str, Any]) -> Optional[Filter]:
        """
        Build Qdrant filter.
        List values → MatchAny (OR semantics).
        Single values → MatchValue (exact match).
        """
        conditions = []
        for key, value in filters.items():
            if isinstance(value, list):
                # OR: match any of the values
                conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
            else:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        return Filter(must=conditions) if conditions else None


# ── Singleton ─────────────────────────────────────────────────────────────────

_qdrant_instance: Optional[QdrantVectorStore] = None


def get_qdrant_client() -> QdrantVectorStore:
    global _qdrant_instance
    if _qdrant_instance is None:
        _qdrant_instance = QdrantVectorStore()
    return _qdrant_instance


qdrant_store = get_qdrant_client()
