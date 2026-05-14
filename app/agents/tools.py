"""
LangChain tools for research assistant agent.
"""
from typing import Optional, List, Dict, Any
from langchain.tools import BaseTool
from pydantic import Field

from app.services.query_service import QueryService
from app.services.summarization_service import SummarizationService
from app.services.literature_service import LiteratureService
from app.retrieval.hybrid_retriever import HybridRetriever
from app.models.schemas import QueryRequest, SummarizeRequest, LiteratureReviewRequest
from app.utils.logger import app_logger


class SearchPapersTool(BaseTool):
    """Tool for searching relevant papers."""
    
    name: str = "search_papers"
    description: str = """
    Search for relevant research papers based on a query.
    Use this when the user wants to find papers on a specific topic.
    Input should be a search query string.
    Returns a list of relevant papers with titles and brief descriptions.
    """
    
    retriever: HybridRetriever = Field(exclude=True)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, query: str) -> str:
        """Search for papers."""
        try:
            import asyncio
            
            # Run async retrieval
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new loop if current one is running
                import nest_asyncio
                nest_asyncio.apply()
            
            chunks = loop.run_until_complete(
                self.retriever.retrieve(query=query, top_k=10)
            )
            
            # Group by paper
            papers = {}
            for chunk in chunks:
                paper_id = chunk.get('paper_id')
                if paper_id not in papers:
                    meta = chunk.get('paper_metadata', {})
                    papers[paper_id] = {
                        'title': meta.get('title', 'Unknown'),
                        'authors': meta.get('authors', []),
                        'year': meta.get('publication_year', 'N/A'),
                        'relevance': chunk.get('score', 0.0)
                    }
            
            # Format results
            result = f"Found {len(papers)} relevant papers:\n\n"
            for i, (paper_id, info) in enumerate(papers.items(), 1):
                authors = ", ".join(info['authors'][:2]) if info['authors'] else "Unknown"
                if len(info['authors']) > 2:
                    authors += " et al."
                
                result += f"{i}. {info['title']}\n"
                result += f"   Authors: {authors} ({info['year']})\n"
                result += f"   Relevance: {info['relevance']:.2f}\n"
                result += f"   Paper ID: {paper_id}\n\n"
            
            return result
            
        except Exception as e:
            app_logger.error(f"Search papers tool error: {e}")
            return f"Error searching papers: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Async version."""
        try:
            chunks = await self.retriever.retrieve(query=query, top_k=10)
            
            papers = {}
            for chunk in chunks:
                paper_id = chunk.get('paper_id')
                if paper_id not in papers:
                    meta = chunk.get('paper_metadata', {})
                    papers[paper_id] = {
                        'title': meta.get('title', 'Unknown'),
                        'authors': meta.get('authors', []),
                        'year': meta.get('publication_year', 'N/A'),
                        'relevance': chunk.get('score', 0.0)
                    }
            
            result = f"Found {len(papers)} relevant papers:\n\n"
            for i, (paper_id, info) in enumerate(papers.items(), 1):
                authors = ", ".join(info['authors'][:2]) if info['authors'] else "Unknown"
                if len(info['authors']) > 2:
                    authors += " et al."
                
                result += f"{i}. {info['title']}\n"
                result += f"   Authors: {authors} ({info['year']})\n"
                result += f"   Relevance: {info['relevance']:.2f}\n"
                result += f"   Paper ID: {paper_id}\n\n"
            
            return result
            
        except Exception as e:
            app_logger.error(f"Search papers tool error: {e}")
            return f"Error searching papers: {str(e)}"


class AnswerQuestionTool(BaseTool):
    """Tool for answering questions using RAG."""
    
    name: str = "answer_question"
    description: str = """
    Answer a specific question about research papers using RAG.
    Use this when the user asks a direct question that needs a detailed answer with citations.
    Input should be the question string.
    Returns a detailed answer with citations from relevant papers.
    """
    
    query_service: QueryService = Field(exclude=True)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, question: str) -> str:
        """Answer question using RAG."""
        try:
            import asyncio
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            
            request = QueryRequest(
                question=question,
                top_k=5,
                include_citations=True
            )
            
            response = loop.run_until_complete(
                self.query_service.query(request)
            )
            
            result = f"Answer:\n{response.answer}\n\n"
            
            if response.citations:
                result += f"Citations ({len(response.citations)}):\n"
                for i, citation in enumerate(response.citations, 1):
                    authors = ", ".join(citation.authors[:2]) if citation.authors else "Unknown"
                    if len(citation.authors) > 2:
                        authors += " et al."
                    result += f"{i}. {citation.paper_title} ({authors})\n"
            
            if response.confidence:
                result += f"\nConfidence: {response.confidence:.2f}\n"
            
            return result
            
        except Exception as e:
            app_logger.error(f"Answer question tool error: {e}")
            return f"Error answering question: {str(e)}"
    
    async def _arun(self, question: str) -> str:
        """Async version."""
        try:
            request = QueryRequest(
                question=question,
                top_k=5,
                include_citations=True
            )
            
            response = await self.query_service.query(request)
            
            result = f"Answer:\n{response.answer}\n\n"
            
            if response.citations:
                result += f"Citations ({len(response.citations)}):\n"
                for i, citation in enumerate(response.citations, 1):
                    authors = ", ".join(citation.authors[:2]) if citation.authors else "Unknown"
                    if len(citation.authors) > 2:
                        authors += " et al."
                    result += f"{i}. {citation.paper_title} ({authors})\n"
            
            if response.confidence:
                result += f"\nConfidence: {response.confidence:.2f}\n"
            
            return result
            
        except Exception as e:
            app_logger.error(f"Answer question tool error: {e}")
            return f"Error answering question: {str(e)}"


class SummarizePaperTool(BaseTool):
    """Tool for summarizing a specific paper."""
    
    name: str = "summarize_paper"
    description: str = """
    Generate a summary of a specific research paper.
    Use this when the user wants a summary of a particular paper.
    Input should be the paper_id.
    Returns a comprehensive summary with key findings.
    """
    
    summarization_service: SummarizationService = Field(exclude=True)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, paper_id: str) -> str:
        """Summarize paper."""
        try:
            import asyncio
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            
            request = SummarizeRequest(
                paper_id=paper_id,
                summary_type="comprehensive"
            )
            
            summary = loop.run_until_complete(
                self.summarization_service.summarize(request)
            )
            
            result = f"Paper: {summary.paper_title}\n\n"
            result += f"Summary:\n{summary.summary}\n\n"
            
            if summary.key_findings:
                result += "Key Findings:\n"
                for finding in summary.key_findings:
                    result += f"- {finding}\n"
                result += "\n"
            
            if summary.methodology:
                result += f"Methodology:\n{summary.methodology}\n\n"
            
            if summary.limitations:
                result += f"Limitations:\n{summary.limitations}\n"
            
            return result
            
        except Exception as e:
            app_logger.error(f"Summarize paper tool error: {e}")
            return f"Error summarizing paper: {str(e)}"
    
    async def _arun(self, paper_id: str) -> str:
        """Async version."""
        try:
            request = SummarizeRequest(
                paper_id=paper_id,
                summary_type="comprehensive"
            )
            
            summary = await self.summarization_service.summarize(request)
            
            result = f"Paper: {summary.paper_title}\n\n"
            result += f"Summary:\n{summary.summary}\n\n"
            
            if summary.key_findings:
                result += "Key Findings:\n"
                for finding in summary.key_findings:
                    result += f"- {finding}\n"
                result += "\n"
            
            if summary.methodology:
                result += f"Methodology:\n{summary.methodology}\n\n"
            
            if summary.limitations:
                result += f"Limitations:\n{summary.limitations}\n"
            
            return result
            
        except Exception as e:
            app_logger.error(f"Summarize paper tool error: {e}")
            return f"Error summarizing paper: {str(e)}"


class ComparePapersTool(BaseTool):
    """Tool for comparing multiple papers."""
    
    name: str = "compare_papers"
    description: str = """
    Compare multiple research papers on a specific aspect.
    Use this when the user wants to compare different papers or approaches.
    Input should be a comparison query (e.g., "Compare BERT and GPT approaches").
    Returns a structured comparison of the papers.
    """
    
    query_service: QueryService = Field(exclude=True)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, comparison_query: str) -> str:
        """Compare papers."""
        try:
            import asyncio
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            
            # Use RAG to get comparison
            request = QueryRequest(
                question=f"Compare and contrast: {comparison_query}",
                top_k=10,
                include_citations=True
            )
            
            response = loop.run_until_complete(
                self.query_service.query(request)
            )
            
            return response.answer
            
        except Exception as e:
            app_logger.error(f"Compare papers tool error: {e}")
            return f"Error comparing papers: {str(e)}"
    
    async def _arun(self, comparison_query: str) -> str:
        """Async version."""
        try:
            request = QueryRequest(
                question=f"Compare and contrast: {comparison_query}",
                top_k=10,
                include_citations=True
            )
            
            response = await self.query_service.query(request)
            return response.answer
            
        except Exception as e:
            app_logger.error(f"Compare papers tool error: {e}")
            return f"Error comparing papers: {str(e)}"


class GenerateLiteratureReviewTool(BaseTool):
    """Tool for generating literature reviews."""
    
    name: str = "generate_literature_review"
    description: str = """
    Generate a comprehensive literature review on a research topic.
    Use this when the user wants a broad overview of research on a topic.
    Input should be the research topic.
    Returns a structured literature review with themes, gaps, and future directions.
    """
    
    literature_service: LiteratureService = Field(exclude=True)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, topic: str) -> str:
        """Generate literature review."""
        try:
            import asyncio
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            
            request = LiteratureReviewRequest(
                topic=topic,
                max_papers=10
            )
            
            review = loop.run_until_complete(
                self.literature_service.generate_review(request)
            )
            
            result = f"Literature Review: {review.topic}\n\n"
            result += f"Overview:\n{review.overview}\n\n"
            
            if review.key_themes:
                result += "Key Themes:\n"
                for theme in review.key_themes:
                    result += f"- {theme}\n"
                result += "\n"
            
            if review.research_gaps:
                result += "Research Gaps:\n"
                for gap in review.research_gaps:
                    result += f"- {gap}\n"
                result += "\n"
            
            if review.future_directions:
                result += "Future Directions:\n"
                for direction in review.future_directions:
                    result += f"- {direction}\n"
                result += "\n"
            
            result += f"Papers Reviewed: {review.num_papers}\n"
            
            return result
            
        except Exception as e:
            app_logger.error(f"Generate literature review tool error: {e}")
            return f"Error generating literature review: {str(e)}"
    
    async def _arun(self, topic: str) -> str:
        """Async version."""
        try:
            request = LiteratureReviewRequest(
                topic=topic,
                max_papers=10
            )
            
            review = await self.literature_service.generate_review(request)
            
            result = f"Literature Review: {review.topic}\n\n"
            result += f"Overview:\n{review.overview}\n\n"
            
            if review.key_themes:
                result += "Key Themes:\n"
                for theme in review.key_themes:
                    result += f"- {theme}\n"
                result += "\n"
            
            if review.research_gaps:
                result += "Research Gaps:\n"
                for gap in review.research_gaps:
                    result += f"- {gap}\n"
                result += "\n"
            
            if review.future_directions:
                result += "Future Directions:\n"
                for direction in review.future_directions:
                    result += f"- {direction}\n"
                result += "\n"
            
            result += f"Papers Reviewed: {review.num_papers}\n"
            
            return result
            
        except Exception as e:
            app_logger.error(f"Generate literature review tool error: {e}")
            return f"Error generating literature review: {str(e)}"


# Export all tools
__all__ = [
    'SearchPapersTool',
    'AnswerQuestionTool',
    'SummarizePaperTool',
    'ComparePapersTool',
    'GenerateLiteratureReviewTool'
]
