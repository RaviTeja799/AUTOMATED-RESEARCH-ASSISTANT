"""
Agent service for orchestrating research assistant agent.
"""
from typing import Dict, Any, Optional
import time

from app.agents.research_agent import ResearchAgent, AgentOrchestrator
from app.services.query_service import QueryService
from app.services.summarization_service import SummarizationService
from app.services.literature_service import LiteratureService
from app.retrieval.hybrid_retriever import HybridRetriever
from app.services.embedding_service import EmbeddingService
from app.utils.logger import app_logger


class AgentService:
    """Service for managing research assistant agent."""
    
    def __init__(
        self,
        es_client,
        embedding_service: EmbeddingService,
        query_service: QueryService,
        summarization_service: SummarizationService,
        literature_service: LiteratureService,
    ):
        self.embedding_service = embedding_service
        self.query_service = query_service
        self.summarization_service = summarization_service
        self.literature_service = literature_service
        self.retriever = HybridRetriever(embedding_service=embedding_service)
        
        # Initialize agent
        self.research_agent = ResearchAgent(
            query_service=query_service,
            summarization_service=summarization_service,
            literature_service=literature_service,
            retriever=self.retriever
        )
        
        # Initialize orchestrator
        self.orchestrator = AgentOrchestrator(self.research_agent)
        
        app_logger.info("AgentService initialized")
    
    async def process_query(
        self,
        query: str,
        use_intent_routing: bool = True,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user query with agent.
        
        Args:
            query: User query
            use_intent_routing: Whether to use intent classification
            session_id: Optional session ID for tracking
            
        Returns:
            Agent response
        """
        start_time = time.time()
        
        app_logger.info(
            f"Processing agent query: {query[:100]}...",
            extra={"session_id": session_id}
        )
        
        try:
            # Process with orchestrator
            result = await self.orchestrator.process(
                query=query,
                use_intent_routing=use_intent_routing
            )
            
            processing_time = time.time() - start_time
            
            # Format response
            response = {
                "answer": result.get('output', ''),
                "intent": result.get('intent', 'UNKNOWN'),
                "steps": self._format_steps(result.get('intermediate_steps', [])),
                "processing_time": processing_time,
                "session_id": session_id
            }
            
            app_logger.info(
                "Agent query processed successfully",
                extra={
                    "intent": response['intent'],
                    "num_steps": len(response['steps']),
                    "processing_time": processing_time,
                    "session_id": session_id
                }
            )
            
            return response
            
        except Exception as e:
            app_logger.error(f"Agent service error: {e}", exc_info=True)
            return {
                "answer": f"I encountered an error: {str(e)}",
                "intent": "ERROR",
                "steps": [],
                "processing_time": time.time() - start_time,
                "session_id": session_id
            }
    
    def _format_steps(self, intermediate_steps: list) -> list:
        """Format intermediate steps for response."""
        formatted_steps = []
        
        for step in intermediate_steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]
                formatted_steps.append({
                    "tool": action.tool if hasattr(action, 'tool') else "unknown",
                    "input": action.tool_input if hasattr(action, 'tool_input') else "",
                    "output": str(observation)[:200] + "..." if len(str(observation)) > 200 else str(observation)
                })
        
        return formatted_steps
    
    def clear_memory(self, session_id: Optional[str] = None):
        """
        Clear agent memory.
        
        Args:
            session_id: Optional session ID
        """
        self.orchestrator.clear_memory()
        app_logger.info(f"Agent memory cleared for session: {session_id}")
    
    def get_conversation_history(self, session_id: Optional[str] = None) -> list:
        """
        Get conversation history.
        
        Args:
            session_id: Optional session ID
            
        Returns:
            Conversation history
        """
        return self.orchestrator.get_conversation_history()


# Export
__all__ = ['AgentService']
