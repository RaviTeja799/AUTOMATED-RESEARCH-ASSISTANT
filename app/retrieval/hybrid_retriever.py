"""
Hybrid retriever combining semantic and keyword search with reranking.
"""
from typing import List, Dict, Any, Optional
import time

from app.retrieval.elasticsearch_client import ElasticsearchClient
from app.retrieval.index_manager import IndexManager
from app.services.embedding_service import EmbeddingService
from app.core.config import settings
from app.core.exceptions import RetrievalError
from app.utils.logger import app_logger


class HybridRetriever:
    """
    Hybrid retriever combining semantic (dense vector) and keyword (BM25) search.
    
    Features:
    - Semantic search using embeddings
    - Keyword search using BM25
    - RRF (Reciprocal Rank Fusion) for combining results
    - Configurable weights
    - Filtering support
    - Reranking support
    """
    
    def __init__(
        self,
        es_client: ElasticsearchClient,
        embedding_service: EmbeddingService,
        semantic_weight: float = 0.5,
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            es_client: Elasticsearch client
            embedding_service: Embedding service
            semantic_weight: Weight for semantic vs keyword (0-1)
        """
        self.es_client = es_client
        self.embedding_service = embedding_service
        self.semantic_weight = semantic_weight
        self.keyword_weight = 1.0 - semantic_weight
        
        app_logger.info(
            f"HybridRetriever initialized with semantic_weight={semantic_weight}"
        )
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        boost_key_sections: bool = True,
        min_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks using hybrid search.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional filters (paper_id, section, date range, etc.)
            boost_key_sections: Boost abstract and conclusion sections
            min_score: Minimum relevance score threshold
            
        Returns:
            List of retrieved chunks with metadata and scores
        """
        start_time = time.time()
        
        try:
            # Generate query embedding
            app_logger.info(f"Generating embedding for query: {query[:100]}...")
            query_embedding = await self.embedding_service.embed_text(query)
            
            # Build hybrid search query
            search_query = IndexManager.get_hybrid_search_query(
                query_text=query,
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters,
                semantic_weight=self.semantic_weight,
                boost_key_sections=boost_key_sections
            )
            
            # Execute search
            app_logger.info(f"Executing hybrid search with top_k={top_k}")
            results = await self.es_client.search(
                index=settings.elasticsearch_index,
                body=search_query
            )
            
            # Process results
            chunks = []
            for hit in results['hits']['hits']:
                chunk = hit['_source']
                chunk['score'] = hit['_score']
                chunk['chunk_id'] = hit['_id']
                
                # Add highlights if available
                if 'highlight' in hit:
                    chunk['highlights'] = hit['highlight']
                
                # Apply minimum score filter
                if min_score is None or chunk['score'] >= min_score:
                    chunks.append(chunk)
            
            elapsed_time = time.time() - start_time
            
            app_logger.info(
                f"Retrieved {len(chunks)} chunks in {elapsed_time:.3f}s",
                extra={
                    "num_results": len(chunks),
                    "retrieval_time": elapsed_time,
                    "top_k": top_k
                }
            )
            
            return chunks
            
        except Exception as e:
            app_logger.error(f"Hybrid retrieval failed: {e}", exc_info=True)
            raise RetrievalError("Failed to retrieve chunks", detail=str(e))
    
    async def retrieve_with_reranking(
        self,
        query: str,
        top_k: int = 5,
        initial_k: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        rerank_method: str = "cross_encoder",
    ) -> List[Dict[str, Any]]:
        """
        Retrieve with reranking for improved relevance.
        
        Args:
            query: Search query
            top_k: Final number of results
            initial_k: Initial retrieval size (before reranking)
            filters: Optional filters
            rerank_method: Reranking method (cross_encoder, llm, etc.)
            
        Returns:
            Reranked chunks
        """
        # Retrieve more candidates
        candidates = await self.retrieve(
            query=query,
            top_k=initial_k,
            filters=filters
        )
        
        if len(candidates) <= top_k:
            return candidates
        
        # Rerank candidates
        app_logger.info(f"Reranking {len(candidates)} candidates to top {top_k}")
        
        if rerank_method == "cross_encoder":
            reranked = await self._rerank_with_cross_encoder(query, candidates)
        elif rerank_method == "llm":
            reranked = await self._rerank_with_llm(query, candidates)
        else:
            # Default: use original scores
            reranked = candidates
        
        return reranked[:top_k]
    
    async def retrieve_by_paper(
        self,
        paper_id: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a specific paper.
        
        Args:
            paper_id: Paper ID
            top_k: Optional limit on number of chunks
            
        Returns:
            List of chunks ordered by chunk_index
        """
        try:
            chunks = await self.es_client.get_paper_chunks(paper_id)
            
            if top_k:
                chunks = chunks[:top_k]
            
            app_logger.info(f"Retrieved {len(chunks)} chunks for paper {paper_id}")
            return chunks
            
        except Exception as e:
            app_logger.error(f"Failed to retrieve paper chunks: {e}")
            raise RetrievalError(f"Failed to retrieve paper {paper_id}", detail=str(e))
    
    async def retrieve_by_section(
        self,
        query: str,
        sections: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chunks from specific sections only.
        
        Args:
            query: Search query
            sections: List of section types (e.g., ['abstract', 'conclusion'])
            top_k: Number of results
            
        Returns:
            Retrieved chunks from specified sections
        """
        filters = {"section": sections}
        return await self.retrieve(
            query=query,
            top_k=top_k,
            filters=filters
        )
    
    async def retrieve_by_date_range(
        self,
        query: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chunks from papers within a date range.
        
        Args:
            query: Search query
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            top_k: Number of results
            
        Returns:
            Retrieved chunks from papers in date range
        """
        filters = {}
        
        if start_year or end_year:
            year_filter = {}
            if start_year:
                year_filter['gte'] = start_year
            if end_year:
                year_filter['lte'] = end_year
            
            filters['paper_metadata.publication_year'] = {'range': year_filter}
        
        return await self.retrieve(
            query=query,
            top_k=top_k,
            filters=filters
        )
    
    async def retrieve_similar_chunks(
        self,
        chunk_id: str,
        top_k: int = 5,
        exclude_same_paper: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find chunks similar to a given chunk.
        
        Args:
            chunk_id: Source chunk ID
            top_k: Number of similar chunks to return
            exclude_same_paper: Exclude chunks from the same paper
            
        Returns:
            Similar chunks
        """
        try:
            # Get source chunk
            source_chunk = await self.es_client.get_chunk(chunk_id)
            
            if not source_chunk:
                raise RetrievalError(f"Chunk {chunk_id} not found")
            
            # Use chunk's embedding for similarity search
            embedding = source_chunk.get('embedding')
            if not embedding:
                raise RetrievalError(f"Chunk {chunk_id} has no embedding")
            
            # Build filters
            filters = None
            if exclude_same_paper:
                paper_id = source_chunk.get('paper_id')
                if paper_id:
                    filters = {'paper_id': {'not': paper_id}}
            
            # Search using embedding
            query = {
                "size": top_k,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": embedding}
                        }
                    }
                }
            }
            
            if filters:
                query["query"]["script_score"]["query"] = {
                    "bool": {"must_not": [{"term": filters}]}
                }
            
            results = await self.es_client.search(
                index=settings.elasticsearch_index,
                body=query
            )
            
            chunks = []
            for hit in results['hits']['hits']:
                if hit['_id'] != chunk_id:  # Exclude source chunk
                    chunk = hit['_source']
                    chunk['score'] = hit['_score']
                    chunk['chunk_id'] = hit['_id']
                    chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            app_logger.error(f"Failed to find similar chunks: {e}")
            raise RetrievalError("Failed to find similar chunks", detail=str(e))
    
    async def _rerank_with_cross_encoder(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rerank using cross-encoder model.
        
        TODO: Implement cross-encoder reranking
        Currently returns candidates as-is.
        """
        app_logger.warning("Cross-encoder reranking not yet implemented")
        return candidates
    
    async def _rerank_with_llm(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rerank using LLM.
        
        TODO: Implement LLM-based reranking
        Currently returns candidates as-is.
        """
        app_logger.warning("LLM reranking not yet implemented")
        return candidates
    
    def set_weights(self, semantic_weight: float) -> None:
        """
        Update semantic/keyword weights.
        
        Args:
            semantic_weight: New semantic weight (0-1)
        """
        if not 0 <= semantic_weight <= 1:
            raise ValueError("semantic_weight must be between 0 and 1")
        
        self.semantic_weight = semantic_weight
        self.keyword_weight = 1.0 - semantic_weight
        
        app_logger.info(
            f"Updated weights: semantic={semantic_weight}, keyword={self.keyword_weight}"
        )


# Export
__all__ = ['HybridRetriever']
