"""
Literature review service - generates structured reviews using Groq.
"""
from datetime import datetime
from typing import List

from app.models.schemas import (
    LiteratureReviewRequest, LiteratureReview, PaperSummaryBrief
)
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.utils.logger import app_logger


LIT_SYSTEM = """You are an expert academic researcher writing literature reviews.
Base everything strictly on the provided paper excerpts.
Be analytical, identify themes, gaps, and future directions."""

LIT_PROMPT = """Write a literature review on: "{topic}"

Papers available:
{papers_text}

Return this exact JSON:
{{
  "overview": "2-3 paragraph overview of the field",
  "key_themes": ["theme 1", "theme 2", "theme 3"],
  "research_gaps": ["gap 1", "gap 2"],
  "future_directions": ["direction 1", "direction 2"]
}}

Return only valid JSON."""


class LiteratureService:
    """Service for literature review generation."""

    def __init__(self, store, embedding_service: EmbeddingService,
                 llm_service: LLMService):
        self.store = store
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        app_logger.info("LiteratureService initialized")

    async def generate_review(self, request: LiteratureReviewRequest) -> LiteratureReview:
        app_logger.info(f"Generating literature review: {request.topic}")

        # Get all paper IDs
        all_ids = await self.store.get_paper_ids()
        if not all_ids:
            return LiteratureReview(
                topic=request.topic,
                overview="No papers are indexed yet. Please upload papers first.",
                papers_reviewed=[],
                key_themes=[],
                research_gaps=[],
                future_directions=[],
                generated_at=datetime.utcnow(),
                num_papers=0,
            )

        # Search for relevant chunks using topic embedding
        topic_embedding = self.embedding_service.embed_query(request.topic)
        results = await self.store.search(
            query_embedding=topic_embedding,
            top_k=min(request.max_papers * 3, 30),
            score_threshold=0.2,
        )

        # Group by paper
        paper_chunks: dict = {}
        for r in results:
            pid = r["paper_id"]
            if pid not in paper_chunks:
                paper_chunks[pid] = {"chunks": [], "meta": r.get("paper_metadata", {})}
            paper_chunks[pid]["chunks"].append(r["text"])

        if not paper_chunks:
            return LiteratureReview(
                topic=request.topic,
                overview=f"No relevant papers found for topic: {request.topic}",
                papers_reviewed=[],
                key_themes=[],
                research_gaps=[],
                future_directions=[],
                generated_at=datetime.utcnow(),
                num_papers=0,
            )

        # Build papers text for prompt
        papers_text_parts = []
        papers_reviewed = []
        for i, (pid, data) in enumerate(list(paper_chunks.items())[:request.max_papers]):
            meta = data["meta"]
            title = meta.get("title", f"Paper {i+1}")
            authors = meta.get("authors", [])
            excerpt = " ".join(data["chunks"][:2])[:800]
            papers_text_parts.append(
                f"Paper {i+1}: {title}\nAuthors: {', '.join(authors) if authors else 'Unknown'}\n{excerpt}"
            )
            papers_reviewed.append(PaperSummaryBrief(
                paper_id=pid,
                title=title,
                authors=authors,
                year=meta.get("publication_date", ""),
                key_contribution=excerpt[:150] + "...",
                relevance_score=results[0]["score"] if results else 0.5,
            ))

        papers_text = "\n\n---\n\n".join(papers_text_parts)
        prompt = LIT_PROMPT.format(topic=request.topic, papers_text=papers_text[:5000])

        try:
            raw = await self.llm_service.generate(
                prompt=prompt,
                system_prompt=LIT_SYSTEM,
                temperature=0.3,
                max_tokens=1500,
            )
            import json, re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            data = json.loads(match.group() if match else raw)

            return LiteratureReview(
                topic=request.topic,
                overview=data.get("overview", raw),
                papers_reviewed=papers_reviewed,
                key_themes=data.get("key_themes", []),
                research_gaps=data.get("research_gaps", []),
                future_directions=data.get("future_directions", []),
                generated_at=datetime.utcnow(),
                num_papers=len(papers_reviewed),
            )
        except Exception as e:
            app_logger.error(f"Literature review generation failed: {e}")
            return LiteratureReview(
                topic=request.topic,
                overview=f"Review generation encountered an error: {e}",
                papers_reviewed=papers_reviewed,
                key_themes=[],
                research_gaps=[],
                future_directions=[],
                generated_at=datetime.utcnow(),
                num_papers=len(papers_reviewed),
            )
