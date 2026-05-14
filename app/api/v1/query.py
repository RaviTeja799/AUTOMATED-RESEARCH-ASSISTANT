"""
Query endpoints for RAG-based question answering.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import QueryRequest, QueryResponse
from app.services.query_service import QueryService
from app.api.deps import get_query_service, get_request_id
from app.core.exceptions import RetrievalError, LLMError
from app.utils.logger import app_logger


router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=QueryResponse)
@router.post("/", response_model=QueryResponse, include_in_schema=False)
async def query_papers(
    request: QueryRequest,
    query_service: QueryService = Depends(get_query_service),
    request_id: str = Depends(get_request_id),
) -> QueryResponse:
    """
    Query research papers using RAG (Retrieval-Augmented Generation).
    
    **Process:**
    1. Generate query embedding
    2. Perform hybrid search (semantic + keyword)
    3. Retrieve top-k relevant chunks
    4. Generate answer using LLM with context
    5. Extract citations from sources
    
    **Args:**
    - **question**: Research question (1-1000 characters)
    - **top_k**: Number of chunks to retrieve (1-20, default: 5)
    - **filters**: Optional filters (e.g., by author, date)
    - **include_citations**: Include source citations (default: true)
    
    **Returns:**
    - Answer with citations and metadata
    
    **Example Request:**
    ```json
    {
        "question": "What are the main findings about transformer architectures?",
        "top_k": 5,
        "include_citations": true
    }
    ```
    
    **Example Response:**
    ```json
    {
        "answer": "Transformer architectures introduced self-attention mechanisms...",
        "citations": [
            {
                "paper_id": "abc123",
                "paper_title": "Attention Is All You Need",
                "authors": ["Vaswani et al."],
                "relevance_score": 0.92,
                "text_snippet": "..."
            }
        ],
        "confidence": 0.85,
        "processing_time": 1.23,
        "retrieved_chunks": 5
    }
    ```
    
    **Raises:**
    - 400: Invalid request
    - 500: Server error
    """
    app_logger.info(f"Processing query: {request.question[:100]}...")
    
    try:
        response = await query_service.query(request)
        
        app_logger.info(
            f"Query processed successfully",
            extra={
                "retrieved_chunks": response.retrieved_chunks,
                "processing_time": response.processing_time,
            }
        )
        
        return response
        
    except RetrievalError as e:
        app_logger.error(f"Retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Retrieval failed", "detail": e.detail}
        )
    except LLMError as e:
        app_logger.error(f"LLM error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Answer generation failed", "detail": e.detail}
        )
    except Exception as e:
        app_logger.error(f"Unexpected error during query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "detail": str(e)}
        )
