"""
Summarization service (stub - to be implemented).
"""
from datetime import datetime

from app.models.schemas import SummarizeRequest, PaperSummary
from app.retrieval.elasticsearch_client import ElasticsearchClient
from app.services.llm_service import LLMService
from app.utils.logger import app_logger


class SummarizationService:
    """Service for paper summarization."""
    
    def __init__(
        self,
        es_client: ElasticsearchClient,
        llm_service: LLMService,
    ):
        """
        Initialize summarization service.
        
        Args:
            es_client: Elasticsearch client
            llm_service: LLM service
        """
        self.es_client = es_client
        self.llm_service = llm_service
        app_logger.info("SummarizationService initialized")
    
    async def summarize(self, request: SummarizeRequest) -> PaperSummary:
        """
        Generate paper summary.
        
        TODO: Implement summarization:
        1. Retrieve paper chunks
        2. Extract key sections
        3. Generate summary with LLM
        4. Extract key findings
        
        Args:
            request: Summarization request
            
        Returns:
            Paper summary
        """
        app_logger.warning("SummarizationService.summarize is a stub - needs implementation")
        
        return PaperSummary(
            paper_id=request.paper_id,
            paper_title="Unknown Paper",
            summary="Summarization not yet implemented.",
            key_findings=[],
            methodology=None,
            limitations=None,
            summary_type=request.summary_type,
            generated_at=datetime.utcnow(),
        )
