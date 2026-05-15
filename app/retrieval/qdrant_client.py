"""
Qdrant Cloud vector store client.
Replaces Elasticsearch for vector search + metadata storage.
"""
from typing import List, Dict, Any, Optional
from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    PayloadSchemaType,
)

from app.core.config import settings
from app.models.schemas import DocumentChunk
from app.utils.logger import app_logger


class QdrantVectorStore:
    """Async Qdrant Cloud client for vector search and document storage."""

    def __init__(self):
        self.url = settings.qdrant_url
        self.api_key = settings.qdrant_api_key
        self.collection = settings.qdrant_collection
        self.dimension = settings.embedding_dimension
        self.client: Optional[AsyncQdrantClient] = None
        app_logger.info(f"QdrantVectorStore configured: {self.url}")

    async def initialize(self):
        """Connect and ensure collection exists."""
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
        """Create collection if it doesn't exist."""
        collections = await self.client.get_collections()
        names = [c.name for c in collections.collections]

        if self.collection not in names:
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=self.dimension,
                    distance=Distance.COSINE,
                ),
            )
            # Create payload indexes for fast filtering
            await self.client.create_payload_index(
                collection_name=self.collection,
                field_name="paper_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            await self.client.create_payload_index(
                collection_name=self.collection,
                field_name="section",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            app_logger.info(f"Created Qdrant collection: {self.collection}")
        else:
            app_logger.info(f"Qdrant collection exists: {self.collection}")

    async def ping(self) -> bool:
        """Check connectivity."""
        try:
            await self.client.get_collections()
            return True
        except Exception as e:
            app_logger.error(f"Qdrant ping failed: {e}")
            return False

    async def index_chunks(
        self,
        chunks: List[DocumentChunk],
        paper_metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Upload chunks with embeddings to Qdrant."""
        if not chunks:
            return 0

        points = []
        for chunk in chunks:
            if not chunk.embedding:
                app_logger.warning(f"Chunk {chunk.chunk_id} has no embedding, skipping")
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

            points.append(
                PointStruct(
                    id=str(uuid4()),
                    vector=chunk.embedding,
                    payload=payload,
                )
            )

        if not points:
            return 0

        # Upload in batches of 100
        batch_size = 100
        total = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            await self.client.upsert(
                collection_name=self.collection,
                points=batch,
            )
            total += len(batch)

        app_logger.info(f"Indexed {total} chunks to Qdrant")
        return total

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Semantic vector search."""
        qdrant_filter = self._build_filter(filters) if filters else None

        results = await self.client.query_points(
            collection_name=self.collection,
            query=query_embedding,
            limit=top_k,
            query_filter=qdrant_filter,
            score_threshold=score_threshold,
            with_payload=True,
        )

        chunks = []
        for hit in results.points:
            payload = hit.payload or {}
            chunks.append({
                "chunk_id": payload.get("chunk_id", ""),
                "paper_id": payload.get("paper_id", ""),
                "text": payload.get("text", ""),
                "section": payload.get("section"),
                "page_number": payload.get("page_number"),
                "chunk_index": payload.get("chunk_index", 0),
                "paper_metadata": payload.get("paper_metadata", {}),
                "metadata": payload.get("metadata", {}),
                "score": hit.score,
            })

        return chunks

    async def get_paper_chunks(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a paper, ordered by chunk_index."""
        results, _ = await self.client.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
            ),
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        chunks = []
        for point in results:
            payload = point.payload or {}
            chunks.append({
                "chunk_id": payload.get("chunk_id", ""),
                "paper_id": payload.get("paper_id", ""),
                "text": payload.get("text", ""),
                "section": payload.get("section"),
                "page_number": payload.get("page_number"),
                "chunk_index": payload.get("chunk_index", 0),
                "paper_metadata": payload.get("paper_metadata", {}),
            })

        return sorted(chunks, key=lambda x: x.get("chunk_index", 0))

    async def get_paper_ids(self) -> List[str]:
        """Get all unique paper IDs."""
        paper_ids = set()
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

        return list(paper_ids)

    async def delete_paper(self, paper_id: str) -> int:
        """Delete all chunks for a paper."""
        result = await self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
            ),
        )
        app_logger.info(f"Deleted chunks for paper {paper_id}: {result.status}")
        return 1  # Qdrant doesn't return count directly

    async def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a single chunk by chunk_id (payload field)."""
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

        point = results[0]
        payload = point.payload or {}
        payload["embedding"] = point.vector
        return payload

    async def close(self):
        """Close the client."""
        if self.client:
            await self.client.close()
            app_logger.info("Qdrant client closed")

    def _build_filter(self, filters: Dict[str, Any]) -> Filter:
        """Convert filter dict to Qdrant Filter."""
        conditions = []
        for key, value in filters.items():
            if isinstance(value, list):
                for v in value:
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=v))
                    )
            else:
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
        return Filter(must=conditions) if conditions else None


# Global lazy instance
_qdrant_instance: Optional[QdrantVectorStore] = None


def get_qdrant_client() -> QdrantVectorStore:
    global _qdrant_instance
    if _qdrant_instance is None:
        _qdrant_instance = QdrantVectorStore()
    return _qdrant_instance


qdrant_store = get_qdrant_client()
