"""
Summarization service - generates structured paper summaries using Groq.
"""
from datetime import datetime
from typing import List, Optional

from app.models.schemas import SummarizeRequest, PaperSummary
from app.services.llm_service import LLMService
from app.core.exceptions import PaperNotFoundError, LLMError
from app.utils.logger import app_logger


SUMMARIZE_SYSTEM = """You are a research paper summarization expert.
Summarize academic papers accurately and concisely.
Always base your summary strictly on the provided text.
Never add information not present in the source."""

SUMMARIZE_PROMPT = """Summarize the following research paper.

Paper sections:
{text}

Provide a {summary_type} summary with this exact JSON structure:
{{
  "title": "paper title",
  "summary": "main summary paragraph",
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "methodology": "brief methodology description",
  "limitations": "limitations if mentioned, else null"
}}

Return only valid JSON, no extra text."""


class SummarizationService:
    """Service for paper summarization using Groq LLM."""

    def __init__(self, es_client, llm_service: LLMService):
        self.store = es_client   # QdrantVectorStore
        self.llm_service = llm_service
        app_logger.info("SummarizationService initialized")

    async def summarize(self, request: SummarizeRequest) -> PaperSummary:
        """Generate a structured summary of a paper."""
        app_logger.info(f"Summarizing paper {request.paper_id} ({request.summary_type})")

        # Get all chunks for this paper
        chunks = await self.store.get_paper_chunks(request.paper_id)
        if not chunks:
            raise PaperNotFoundError(f"Paper not found: {request.paper_id}")

        # Get paper title from metadata
        paper_title = "Unknown Paper"
        if chunks and chunks[0].get("paper_metadata", {}).get("title"):
            paper_title = chunks[0]["paper_metadata"]["title"]

        # Build text from key sections in priority order
        section_priority = ["abstract", "introduction", "results",
                            "conclusion", "methodology", "methods", "unknown"]
        sections: dict = {}
        for chunk in chunks:
            sec = (chunk.get("section") or "unknown").lower()
            if sec not in sections:
                sections[sec] = []
            sections[sec].append(chunk["text"])

        # Assemble text respecting token budget (~6000 chars)
        assembled = []
        budget = 6000
        for sec in section_priority:
            if sec in sections:
                block = f"[{sec.upper()}]\n" + " ".join(sections[sec])
                if len(block) > budget:
                    block = block[:budget]
                assembled.append(block)
                budget -= len(block)
                if budget <= 0:
                    break

        # Add any remaining sections
        for sec, texts in sections.items():
            if sec not in section_priority and budget > 0:
                block = f"[{sec.upper()}]\n" + " ".join(texts)[:budget]
                assembled.append(block)
                budget -= len(block)

        full_text = "\n\n".join(assembled)

        # Generate summary
        prompt = SUMMARIZE_PROMPT.format(
            text=full_text,
            summary_type=request.summary_type,
        )

        try:
            raw = await self.llm_service.generate(
                prompt=prompt,
                system_prompt=SUMMARIZE_SYSTEM,
                temperature=0.2,
                max_tokens=1024,
            )

            # Parse JSON response
            import json, re
            # Extract JSON block if wrapped in markdown
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                data = json.loads(raw)

            return PaperSummary(
                paper_id=request.paper_id,
                paper_title=data.get("title", paper_title),
                summary=data.get("summary", raw),
                key_findings=data.get("key_findings", []),
                methodology=data.get("methodology"),
                limitations=data.get("limitations"),
                summary_type=request.summary_type,
                generated_at=datetime.utcnow(),
            )

        except Exception as e:
            app_logger.error(f"Summarization failed: {e}")
            # Fallback: return raw LLM output
            return PaperSummary(
                paper_id=request.paper_id,
                paper_title=paper_title,
                summary=raw if 'raw' in dir() else str(e),
                key_findings=[],
                methodology=None,
                limitations=None,
                summary_type=request.summary_type,
                generated_at=datetime.utcnow(),
            )
