"""
Elasticsearch client — no-op stub.
This project now uses Qdrant Cloud for vector storage.
Kept for import compatibility only.
"""
from app.utils.logger import app_logger


class ElasticsearchClient:
    """No-op stub — QdrantVectorStore is the active vector store."""

    def __init__(self, *args, **kwargs):
        app_logger.debug("ElasticsearchClient stub (Qdrant is active)")

    async def initialize(self): pass
    async def ping(self): return False
    async def health_check(self): return False
    async def close(self): pass
    async def index_chunks(self, *a, **kw): return 0
    async def get_paper_chunks(self, *a, **kw): return []
    async def get_paper_ids(self, *a, **kw): return []
    async def delete_paper(self, *a, **kw): return 0
    async def get_chunk(self, *a, **kw): return None
    async def search(self, *a, **kw): return {"hits": {"hits": []}}


_instance = None


def get_es_client() -> ElasticsearchClient:
    global _instance
    if _instance is None:
        _instance = ElasticsearchClient()
    return _instance


es_client = get_es_client()
