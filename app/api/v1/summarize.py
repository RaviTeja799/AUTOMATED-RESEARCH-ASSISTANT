"""
Paper summarization endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import SummarizeRequest, PaperSummary
from app.services.summarization_service import SummarizationService
from app.api.deps import get_summarization_service, get_request_id
from app.core.exceptions import PaperNotFoundError, LLMError
from app.utils.logger import app_logger


router = APIRouter(prefix="/summarize", tags=["Summarization"])


@router.post("", response_model=PaperSummary)
@router.post("/", response_model=PaperSummary, include_in_schema=False)
async def summarize_paper(
    request: SummarizeRequest,
    summarization_service: SummarizationService = Depends(get_summarization_service),
    request_id: str = Depends(get_request_id),
) -> PaperSummary:
    """
    Generate a comprehensive summary of a research paper.
    
    **Process:**
    1. Retrieve all chunks for the paper
    2. Extract key sections (abstract, intro, methods, results, conclusion)
    3. Generate structured summary using LLM
    4. Extract key findings and methodology
    
    **Args:**
    - **paper_id**: Unique paper identifier
    - **summary_type**: Type of summary (brief, comprehensive, technical)
    - **max_length**: Maximum summary length in words (100-2000)
    
    **Summary Types:**
    - **brief**: Short overview (200-300 words)
    - **comprehensive**: Detailed summary with all sections (500-800 words)
    - **technical**: Technical deep-dive with methodology details (800-1500 words)
    
    **Returns:**
    - Structured paper summary with key findings
    
    **Example Request:**
    ```json
    {
        "paper_id": "abc123",
        "summary_type": "comprehensive",
        "max_length": 500
    }
    ```
    
    **Example Response:**
    ```json
    {
        "paper_id": "abc123",
        "paper_title": "Attention Is All You Need",
        "summary": "This paper introduces the Transformer architecture...",
        "key_findings": [
            "Self-attention mechanism eliminates need for recurrence",
            "Achieves state-of-the-art results on translation tasks"
        ],
        "methodology": "The authors propose a novel architecture based on...",
        "limitations": "The model requires significant computational resources...",
        "summary_type": "comprehensive",
        "generated_at": "2024-01-15T10:30:00Z"
    }
    ```
    
    **Raises:**
    - 404: Paper not found
    - 500: Server error
    """
    app_logger.info(f"Generating {request.summary_type} summary for paper: {request.paper_id}")
    
    try:
        summary = await summarization_service.summarize(request)
        
        app_logger.info(
            f"Summary generated successfully for paper: {request.paper_id}",
            extra={"summary_type": request.summary_type}
        )
        
        return summary
        
    except PaperNotFoundError as e:
        app_logger.error(f"Paper not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "detail": e.detail}
        )
    except LLMError as e:
        app_logger.error(f"LLM error during summarization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Summarization failed", "detail": e.detail}
        )
    except Exception as e:
        app_logger.error(f"Unexpected error during summarization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "detail": str(e)}
        )
