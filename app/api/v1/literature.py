"""
Literature review generation endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import LiteratureReviewRequest, LiteratureReview
from app.services.literature_service import LiteratureService
from app.api.deps import get_literature_service, get_request_id
from app.core.exceptions import RetrievalError, LLMError
from app.utils.logger import app_logger


router = APIRouter(prefix="/literature-review", tags=["Literature Review"])


@router.post("", response_model=LiteratureReview)
@router.post("/", response_model=LiteratureReview, include_in_schema=False)
async def generate_literature_review(
    request: LiteratureReviewRequest,
    literature_service: LiteratureService = Depends(get_literature_service),
    request_id: str = Depends(get_request_id),
) -> LiteratureReview:
    """
    Generate a comprehensive literature review on a research topic.
    
    **Process:**
    1. Search for relevant papers on the topic
    2. Retrieve and analyze top papers
    3. Extract key contributions from each paper
    4. Identify common themes and patterns
    5. Detect research gaps
    6. Suggest future research directions
    7. Generate structured literature review
    
    **Args:**
    - **topic**: Research topic (3-500 characters)
    - **max_papers**: Maximum papers to include (1-50, default: 10)
    - **focus_areas**: Optional list of specific focus areas
    - **date_range**: Optional date range filter
    
    **Returns:**
    - Comprehensive literature review with themes and gaps
    
    **Example Request:**
    ```json
    {
        "topic": "transformer models in natural language processing",
        "max_papers": 10,
        "focus_areas": ["attention mechanisms", "pre-training"],
        "date_range": {
            "start": "2017-01-01",
            "end": "2024-01-01"
        }
    }
    ```
    
    **Example Response:**
    ```json
    {
        "topic": "transformer models in natural language processing",
        "overview": "Transformer models have revolutionized NLP...",
        "papers_reviewed": [
            {
                "paper_id": "abc123",
                "title": "Attention Is All You Need",
                "authors": ["Vaswani et al."],
                "year": "2017",
                "key_contribution": "Introduced self-attention mechanism",
                "relevance_score": 0.95
            }
        ],
        "key_themes": [
            "Self-attention mechanisms",
            "Pre-training strategies",
            "Transfer learning"
        ],
        "research_gaps": [
            "Limited work on low-resource languages",
            "Computational efficiency remains a challenge"
        ],
        "future_directions": [
            "Efficient transformer architectures",
            "Multimodal transformers"
        ],
        "generated_at": "2024-01-15T10:30:00Z",
        "num_papers": 10
    }
    ```
    
    **Raises:**
    - 400: Invalid request
    - 500: Server error
    """
    app_logger.info(f"Generating literature review for topic: {request.topic}")
    
    try:
        review = await literature_service.generate_review(request)
        
        app_logger.info(
            f"Literature review generated successfully",
            extra={
                "topic": request.topic,
                "num_papers": review.num_papers,
            }
        )
        
        return review
        
    except RetrievalError as e:
        app_logger.error(f"Retrieval error during literature review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Paper retrieval failed", "detail": e.detail}
        )
    except LLMError as e:
        app_logger.error(f"LLM error during literature review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Review generation failed", "detail": e.detail}
        )
    except Exception as e:
        app_logger.error(f"Unexpected error during literature review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "detail": str(e)}
        )
