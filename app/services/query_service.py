"""
Query service for RAG-based question answering with citation-awareness.
"""
import time
import re
from typing import List, Dict, Any, Optional

from app.models.schemas import QueryRequest, QueryResponse, Citation
from app.retrieval.elasticsearch_client import ElasticsearchClient
from app.retrieval.hybrid_retriever import HybridRetriever
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.prompts.rag_prompts import RAGPrompts, HallucinationPrevention
from app.core.config import settings
from app.core.exceptions import RetrievalError, LLMError
from app.utils.logger import app_logger


class QueryService:
    """Service for RAG-based query processing with citation-awareness."""
    
    def __init__(
        self,
        es_client: ElasticsearchClient,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
    ):
        """
        Initialize query service.
        
        Args:
            es_client: Elasticsearch client
            embedding_service: Embedding service
            llm_service: LLM service
        """
        self.es_client = es_client
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        
        # Initialize hybrid retriever
        self.retriever = HybridRetriever(
            es_client=es_client,
            embedding_service=embedding_service,
            semantic_weight=settings.hybrid_search_weight
        )
        
        app_logger.info("QueryService initialized with hybrid retrieval")
    
    async def query(self, request: QueryRequest) -> QueryResponse:
        """
        Process query using RAG pipeline with citation-awareness.
        
        Pipeline:
        1. Retrieve relevant chunks (hybrid search)
        2. Build citation-aware prompt
        3. Generate answer with LLM
        4. Extract citations
        5. Validate answer (hallucination check)
        
        Args:
            request: Query request
            
        Returns:
            Query response with answer and citations
        """
        start_time = time.time()
        
        app_logger.info(
            f"Processing query: {request.question[:100]}...",
            extra={"top_k": request.top_k}
        )
        
        try:
            # Step 1: Retrieve relevant chunks
            chunks = await self._retrieve_chunks(request)
            
            if not chunks:
                return self._create_no_results_response(request, start_time)
            
            # Step 2: Build citation-aware prompt
            prompt = RAGPrompts.build_rag_prompt(
                question=request.question,
                context_chunks=chunks,
                include_confidence=True
            )
            
            # Step 3: Generate answer with LLM
            answer = await self._generate_answer(prompt)
            
            # Step 4: Extract citations from answer
            citations = self._extract_citations(answer, chunks) if request.include_citations else []
            
            # Step 5: Validate answer (basic hallucination check)
            confidence = self._assess_confidence(answer, chunks)
            
            # Step 6: Clean answer (remove confidence section if present)
            clean_answer = self._clean_answer(answer)
            
            processing_time = time.time() - start_time
            
            app_logger.info(
                f"Query processed successfully",
                extra={
                    "retrieved_chunks": len(chunks),
                    "num_citations": len(citations),
                    "confidence": confidence,
                    "processing_time": processing_time
                }
            )
            
            return QueryResponse(
                answer=clean_answer,
                citations=citations,
                confidence=confidence,
                processing_time=processing_time,
                retrieved_chunks=len(chunks)
            )
            
        except RetrievalError as e:
            app_logger.error(f"Retrieval error: {e}")
            raise
        except LLMError as e:
            app_logger.error(f"LLM error: {e}")
            raise
        except Exception as e:
            app_logger.error(f"Unexpected error in query processing: {e}", exc_info=True)
            raise LLMError("Failed to process query", detail=str(e))
    
    async def _retrieve_chunks(self, request: QueryRequest) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks using hybrid search.
        
        Args:
            request: Query request
            
        Returns:
            Retrieved chunks
        """
        try:
            # Determine if we should boost key sections
            boost_key_sections = self._should_boost_key_sections(request.question)
            
            # Retrieve chunks
            chunks = await self.retriever.retrieve(
                query=request.question,
                top_k=request.top_k,
                filters=request.filters,
                boost_key_sections=boost_key_sections,
                min_score=settings.min_similarity_score
            )
            
            return chunks
            
        except Exception as e:
            app_logger.error(f"Chunk retrieval failed: {e}")
            raise RetrievalError("Failed to retrieve relevant chunks", detail=str(e))
    
    async def _generate_answer(self, prompt: str) -> str:
        """
        Generate answer using LLM.
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            Generated answer
        """
        try:
            answer = await self.llm_service.generate(
                prompt=prompt,
                system_prompt=RAGPrompts.SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for factual answers
                max_tokens=settings.ollama_max_tokens
            )
            
            return answer
            
        except Exception as e:
            app_logger.error(f"Answer generation failed: {e}")
            raise LLMError("Failed to generate answer", detail=str(e))
    
    def _extract_citations(
        self,
        answer: str,
        chunks: List[Dict[str, Any]]
    ) -> List[Citation]:
        """
        Extract citations from answer and match with source chunks.
        
        Args:
            answer: Generated answer
            chunks: Source chunks
            
        Returns:
            List of citations
        """
        citations = []
        seen_papers = set()
        
        # Pattern to match citations: [Title, Authors, Year]
        citation_pattern = r'\[([^\]]+),\s*([^\]]+),\s*(\d{4})\]'
        
        for chunk in chunks:
            paper_meta = chunk.get('paper_metadata', {})
            paper_id = chunk.get('paper_id', '')
            title = paper_meta.get('title', 'Unknown Paper')
            authors = paper_meta.get('authors', [])
            
            # Skip if we've already added this paper
            if paper_id in seen_papers:
                continue
            
            # Check if this paper is cited in the answer
            # Look for title or authors in the answer
            title_mentioned = title.lower() in answer.lower()
            authors_mentioned = any(
                author.lower() in answer.lower()
                for author in authors
            ) if authors else False
            
            if title_mentioned or authors_mentioned:
                # Extract text snippet
                text_snippet = chunk.get('text', '')[:200]
                if len(chunk.get('text', '')) > 200:
                    text_snippet += "..."
                
                citation = Citation(
                    paper_id=paper_id,
                    paper_title=title,
                    authors=authors,
                    chunk_id=chunk.get('chunk_id', ''),
                    page_number=chunk.get('page_number'),
                    relevance_score=chunk.get('score', 0.0),
                    text_snippet=text_snippet
                )
                
                citations.append(citation)
                seen_papers.add(paper_id)
        
        return citations
    
    def _assess_confidence(
        self,
        answer: str,
        chunks: List[Dict[str, Any]]
    ) -> Optional[float]:
        """
        Assess confidence in the answer.
        
        Args:
            answer: Generated answer
            chunks: Source chunks
            
        Returns:
            Confidence score (0-1) or None
        """
        # Check if answer explicitly states lack of information
        no_info_phrases = [
            "don't have information",
            "not in the provided",
            "cannot find",
            "insufficient information",
            "not mentioned",
            "unclear from the sources"
        ]
        
        answer_lower = answer.lower()
        
        if any(phrase in answer_lower for phrase in no_info_phrases):
            return 0.3  # Low confidence
        
        # Check for uncertainty phrases
        uncertainty_phrases = [
            "may", "might", "possibly", "perhaps",
            "suggests", "appears", "seems",
            "limited information", "based on available"
        ]
        
        uncertainty_count = sum(
            1 for phrase in uncertainty_phrases
            if phrase in answer_lower
        )
        
        # Check for citations (presence of brackets)
        citation_count = answer.count('[')
        
        # Calculate confidence based on:
        # 1. Presence of citations
        # 2. Lack of uncertainty phrases
        # 3. Average chunk relevance score
        
        avg_chunk_score = sum(c.get('score', 0) for c in chunks) / len(chunks) if chunks else 0
        
        # Normalize to 0-1
        citation_factor = min(citation_count / 5, 1.0)  # Expect ~5 citations
        uncertainty_factor = max(0, 1.0 - (uncertainty_count * 0.2))
        relevance_factor = min(avg_chunk_score / 10, 1.0)  # Normalize score
        
        confidence = (citation_factor * 0.4 + uncertainty_factor * 0.3 + relevance_factor * 0.3)
        
        return round(confidence, 2)
    
    def _clean_answer(self, answer: str) -> str:
        """
        Clean answer by removing confidence assessment section.
        
        Args:
            answer: Raw answer
            
        Returns:
            Cleaned answer
        """
        # Remove confidence assessment section if present
        confidence_markers = [
            "CONFIDENCE ASSESSMENT:",
            "Confidence Level:",
            "Confidence:",
            "VERIFICATION:"
        ]
        
        for marker in confidence_markers:
            if marker in answer:
                answer = answer.split(marker)[0].strip()
                break
        
        return answer
    
    def _should_boost_key_sections(self, question: str) -> bool:
        """
        Determine if key sections should be boosted based on question type.
        
        Args:
            question: User question
            
        Returns:
            True if key sections should be boosted
        """
        # Boost for overview/summary questions
        overview_keywords = [
            "what is", "overview", "summary", "main",
            "key", "primary", "introduce", "explain"
        ]
        
        question_lower = question.lower()
        
        return any(keyword in question_lower for keyword in overview_keywords)
    
    def _create_no_results_response(
        self,
        request: QueryRequest,
        start_time: float
    ) -> QueryResponse:
        """
        Create response when no relevant chunks are found.
        
        Args:
            request: Query request
            start_time: Start time
            
        Returns:
            No results response
        """
        processing_time = time.time() - start_time
        
        answer = (
            "I don't have any relevant information in the indexed papers to answer this question. "
            "This could mean:\n"
            "1. No papers in the database discuss this topic\n"
            "2. The question is too specific or uses different terminology\n"
            "3. Try rephrasing your question or using different keywords"
        )
        
        return QueryResponse(
            answer=answer,
            citations=[],
            confidence=0.0,
            processing_time=processing_time,
            retrieved_chunks=0
        )


# Export
__all__ = ['QueryService']
