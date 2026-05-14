"""
Agent endpoints for research assistant.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.agent_service import AgentService
from app.api.deps import (
    get_elasticsearch_client,
    get_embedding_service,
    get_query_service,
    get_summarization_service,
    get_literature_service,
    get_request_id
)
from app.retrieval.elasticsearch_client import ElasticsearchClient
from app.services.embedding_service import EmbeddingService
from app.services.query_service import QueryService
from app.services.summarization_service import SummarizationService
from app.services.literature_service import LiteratureService
from app.utils.logger import app_logger


router = APIRouter(prefix="/agent", tags=["Agent"])


# Request/Response models
class AgentQueryRequest(BaseModel):
    """Agent query request."""
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    use_intent_routing: bool = Field(default=True, description="Use intent classification")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation tracking")


class AgentStep(BaseModel):
    """Agent intermediate step."""
    tool: str
    input: str
    output: str


class AgentQueryResponse(BaseModel):
    """Agent query response."""
    answer: str
    intent: str
    steps: list[AgentStep]
    processing_time: float
    session_id: Optional[str] = None


class ClearMemoryRequest(BaseModel):
    """Clear memory request."""
    session_id: Optional[str] = Field(default=None, description="Session ID")


# Dependency to get agent service
async def get_agent_service(
    es_client: ElasticsearchClient = Depends(get_elasticsearch_client),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    query_service: QueryService = Depends(get_query_service),
    summarization_service: SummarizationService = Depends(get_summarization_service),
    literature_service: LiteratureService = Depends(get_literature_service),
) -> AgentService:
    """Get agent service instance."""
    return AgentService(
        es_client=es_client,
        embedding_service=embedding_service,
        query_service=query_service,
        summarization_service=summarization_service,
        literature_service=literature_service
    )


@router.post("", response_model=AgentQueryResponse)
@router.post("/", response_model=AgentQueryResponse, include_in_schema=False)
async def query_agent(
    request: AgentQueryRequest,
    agent_service: AgentService = Depends(get_agent_service),
    request_id: str = Depends(get_request_id),
) -> AgentQueryResponse:
    """
    Query the research assistant agent.
    
    The agent will:
    1. Determine user intent
    2. Select appropriate tools
    3. Execute tools in sequence
    4. Synthesize results
    
    **Available Capabilities:**
    - Search for relevant papers
    - Answer specific questions with citations
    - Summarize papers
    - Compare different papers/approaches
    - Generate literature reviews
    
    **Example Queries:**
    - "Find papers about transformers in NLP"
    - "What are the main findings about BERT?"
    - "Compare BERT and GPT approaches"
    - "Generate a literature review on attention mechanisms"
    
    **Args:**
    - **query**: Your research question or request
    - **use_intent_routing**: Enable automatic intent classification (recommended)
    - **session_id**: Optional session ID for conversation tracking
    
    **Returns:**
    - Answer with citations and sources
    - Detected intent
    - Intermediate steps taken
    - Processing time
    
    **Example Request:**
    ```json
    {
        "query": "What are transformers and how do they work?",
        "use_intent_routing": true,
        "session_id": "user-123"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "answer": "Transformers are neural network architectures...",
        "intent": "QUESTION",
        "steps": [
            {
                "tool": "answer_question",
                "input": "What are transformers...",
                "output": "Transformers are..."
            }
        ],
        "processing_time": 2.34,
        "session_id": "user-123"
    }
    ```
    """
    app_logger.info(f"Agent query received: {request.query[:100]}...")
    
    try:
        response = await agent_service.process_query(
            query=request.query,
            use_intent_routing=request.use_intent_routing,
            session_id=request.session_id
        )
        
        return AgentQueryResponse(**response)
        
    except Exception as e:
        app_logger.error(f"Agent query error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Agent processing failed", "detail": str(e)}
        )


@router.post("/clear-memory", status_code=status.HTTP_204_NO_CONTENT)
async def clear_agent_memory(
    request: ClearMemoryRequest,
    agent_service: AgentService = Depends(get_agent_service),
    request_id: str = Depends(get_request_id),
) -> None:
    """
    Clear agent conversation memory.
    
    Use this to start a fresh conversation or reset the agent's context.
    
    **Args:**
    - **session_id**: Optional session ID to clear specific session
    
    **Returns:**
    - 204 No Content on success
    """
    try:
        agent_service.clear_memory(session_id=request.session_id)
        app_logger.info(f"Agent memory cleared for session: {request.session_id}")
        
    except Exception as e:
        app_logger.error(f"Clear memory error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to clear memory", "detail": str(e)}
        )


@router.get("/conversation-history")
async def get_conversation_history(
    session_id: Optional[str] = None,
    agent_service: AgentService = Depends(get_agent_service),
    request_id: str = Depends(get_request_id),
) -> dict:
    """
    Get conversation history for a session.
    
    **Args:**
    - **session_id**: Optional session ID
    
    **Returns:**
    - Conversation history
    """
    try:
        history = agent_service.get_conversation_history(session_id=session_id)
        
        return {
            "session_id": session_id,
            "messages": [
                {
                    "type": msg.type if hasattr(msg, 'type') else "unknown",
                    "content": msg.content if hasattr(msg, 'content') else str(msg)
                }
                for msg in history
            ],
            "count": len(history)
        }
        
    except Exception as e:
        app_logger.error(f"Get history error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get history", "detail": str(e)}
        )
