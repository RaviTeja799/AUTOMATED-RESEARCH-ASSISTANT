"""
Elasticsearch client for document storage and retrieval.
"""
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch, AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from app.core.config import settings
from app.models.schemas import DocumentChunk
from app.utils.logger import app_logger


class ElasticsearchClient:
    """Elasticsearch client for hybrid search."""
    
    def __init__(self):
        self.logger = app_logger
        self.index_name = settings.elasticsearch_index
        
        # Connection parameters
        es_params = {
            "hosts": [settings.elasticsearch_url],
            "verify_certs": False,
            "request_timeout": 30,
        }
        
        if settings.elasticsearch_username and settings.elasticsearch_password:
            es_params["basic_auth"] = (
                settings.elasticsearch_username,
                settings.elasticsearch_password
            )
        
        # Async client for API endpoints
        self.client = AsyncElasticsearch(**es_params)
        
        # Sync client for initialization
        self._sync_client = Elasticsearch(**es_params)
        
        self.logger.info(f"Elasticsearch client initialized: {settings.elasticsearch_url}")
    
    async def initialize(self):
        """Initialize index with proper mappings."""
        try:
            # Check if index exists
            if not await self.client.indices.exists(index=self.index_name):
                await self.create_index()
                self.logger.info(f"Created index: {self.index_name}")
            else:
                self.logger.info(f"Index already exists: {self.index_name}")
        except Exception as e:
            self.logger.error(f"Error initializing Elasticsearch: {e}")
            raise
    
    async def create_index(self):
        """Create index with mappings for hybrid search."""
        mappings = {
            "properties": {
                "chunk_id": {"type": "keyword"},
                "paper_id": {"type": "keyword"},
                "text": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "section": {"type": "keyword"},
                "page_number": {"type": "integer"},
                "chunk_index": {"type": "integer"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": settings.embedding_dimension,
                    "index": True,
                    "similarity": "cosine"
                },
                "metadata": {"type": "object"},
                "paper_metadata": {
                    "properties": {
                        "title": {"type": "text"},
                        "authors": {"type": "keyword"},
                        "abstract": {"type": "text"},
                        "publication_date": {"type": "date", "format": "yyyy-MM-dd||yyyy"},
                        "doi": {"type": "keyword"},
                        "keywords": {"type": "keyword"}
                    }
                },
                "created_at": {"type": "date"}
            }
        }
        
        settings_config = {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "default": {
                        "type": "standard"
                    }
                }
            }
        }
        
        await self.client.indices.create(
            index=self.index_name,
            mappings=mappings,
            settings=settings_config
        )
    
    async def index_chunks(
        self,
        chunks: List[DocumentChunk],
        paper_metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Index document chunks with embeddings.
        
        Args:
            chunks: List of DocumentChunk objects
            paper_metadata: Optional paper metadata to attach to each chunk
            
        Returns:
            Number of chunks indexed
        """
        actions = []
        
        for chunk in chunks:
            doc = {
                "_index": self.index_name,
                "_id": chunk.chunk_id,
                "_source": {
                    "chunk_id": chunk.chunk_id,
                    "paper_id": chunk.paper_id,
                    "text": chunk.text,
                    "section": chunk.section,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "embedding": chunk.embedding,
                    "metadata": chunk.metadata,
                    "paper_metadata": paper_metadata or {},
                    "created_at": "now"
                }
            }
            actions.append(doc)
        
        try:
            success, failed = await async_bulk(
                self.client,
                actions,
                raise_on_error=False
            )
            
            self.logger.info(f"Indexed {success} chunks, {len(failed)} failed")
            return success
            
        except Exception as e:
            self.logger.error(f"Error indexing chunks: {e}")
            raise
    
    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        semantic_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword search.
        
        Args:
            query_text: Text query for keyword search
            query_embedding: Embedding vector for semantic search
            top_k: Number of results to return
            filters: Optional filters (e.g., paper_id, section)
            semantic_weight: Weight for semantic vs keyword (0-1)
            
        Returns:
            List of search results with scores
        """
        # Build filter query
        filter_clauses = []
        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    filter_clauses.append({"terms": {field: value}})
                else:
                    filter_clauses.append({"term": {field: value}})
        
        # Semantic search query (KNN)
        knn_query = {
            "field": "embedding",
            "query_vector": query_embedding,
            "k": top_k * 2,  # Get more candidates
            "num_candidates": top_k * 10
        }
        
        if filter_clauses:
            knn_query["filter"] = filter_clauses
        
        # Keyword search query (BM25)
        text_query = {
            "bool": {
                "should": [
                    {"match": {"text": {"query": query_text, "boost": 1.0}}},
                    {"match": {"paper_metadata.title": {"query": query_text, "boost": 2.0}}},
                    {"match": {"paper_metadata.abstract": {"query": query_text, "boost": 1.5}}}
                ],
                "minimum_should_match": 1
            }
        }
        
        if filter_clauses:
            text_query["bool"]["filter"] = filter_clauses
        
        # Combine queries with RRF (Reciprocal Rank Fusion)
        search_body = {
            "size": top_k,
            "query": text_query,
            "knn": knn_query,
            "rank": {
                "rrf": {
                    "window_size": top_k * 2,
                    "rank_constant": 60
                }
            },
            "_source": {
                "excludes": ["embedding"]  # Don't return embeddings
            }
        }
        
        try:
            response = await self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "chunk_id": hit["_source"]["chunk_id"],
                    "paper_id": hit["_source"]["paper_id"],
                    "text": hit["_source"]["text"],
                    "section": hit["_source"].get("section"),
                    "page_number": hit["_source"].get("page_number"),
                    "score": hit["_score"],
                    "paper_metadata": hit["_source"].get("paper_metadata", {})
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error performing hybrid search: {e}")
            raise
    
    async def get_paper_chunks(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific paper."""
        query = {
            "query": {
                "term": {"paper_id": paper_id}
            },
            "sort": [{"chunk_index": "asc"}],
            "size": 10000,
            "_source": {"excludes": ["embedding"]}
        }
        
        try:
            response = await self.client.search(
                index=self.index_name,
                body=query
            )
            
            chunks = [hit["_source"] for hit in response["hits"]["hits"]]
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error getting paper chunks: {e}")
            raise
    
    async def delete_paper(self, paper_id: str) -> int:
        """Delete all chunks for a paper."""
        query = {
            "query": {
                "term": {"paper_id": paper_id}
            }
        }
        
        try:
            response = await self.client.delete_by_query(
                index=self.index_name,
                body=query
            )
            
            deleted = response.get("deleted", 0)
            self.logger.info(f"Deleted {deleted} chunks for paper {paper_id}")
            return deleted
            
        except Exception as e:
            self.logger.error(f"Error deleting paper: {e}")
            raise
    
    async def get_paper_ids(self) -> List[str]:
        """Get all unique paper IDs."""
        query = {
            "size": 0,
            "aggs": {
                "unique_papers": {
                    "terms": {
                        "field": "paper_id",
                        "size": 10000
                    }
                }
            }
        }
        
        try:
            response = await self.client.search(
                index=self.index_name,
                body=query
            )
            
            buckets = response["aggregations"]["unique_papers"]["buckets"]
            paper_ids = [bucket["key"] for bucket in buckets]
            return paper_ids
            
        except Exception as e:
            self.logger.error(f"Error getting paper IDs: {e}")
            raise
    
    async def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a single chunk by ID."""
        try:
            response = await self.client.get(
                index=self.index_name,
                id=chunk_id
            )
            return response['_source']
        except Exception as e:
            self.logger.error(f"Error getting chunk: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check if Elasticsearch is healthy."""
        try:
            health = await self.client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            self.logger.error(f"Elasticsearch health check failed: {e}")
            return False

    async def ping(self) -> bool:
        """Ping Elasticsearch to check connectivity."""
        try:
            return await self.client.ping()
        except Exception as e:
            self.logger.error(f"Elasticsearch ping failed: {e}")
            return False
    
    async def close(self):
        """Close Elasticsearch connection."""
        await self.client.close()
        self._sync_client.close()


# Global instance
es_client = ElasticsearchClient()
