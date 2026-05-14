"""Prompt templates for LLM interactions."""
from app.prompts.templates import (
    RAG_SYSTEM_PROMPT,
    RAG_QUERY_TEMPLATE,
    RAG_QUERY_WITH_CITATIONS_TEMPLATE,
    SUMMARIZE_BRIEF_TEMPLATE,
    SUMMARIZE_COMPREHENSIVE_TEMPLATE,
    SUMMARIZE_TECHNICAL_TEMPLATE,
    LITERATURE_REVIEW_TEMPLATE,
    AGENT_SYSTEM_PROMPT,
    format_context_for_rag,
    format_papers_for_review,
)

__all__ = [
    "RAG_SYSTEM_PROMPT",
    "RAG_QUERY_TEMPLATE",
    "RAG_QUERY_WITH_CITATIONS_TEMPLATE",
    "SUMMARIZE_BRIEF_TEMPLATE",
    "SUMMARIZE_COMPREHENSIVE_TEMPLATE",
    "SUMMARIZE_TECHNICAL_TEMPLATE",
    "LITERATURE_REVIEW_TEMPLATE",
    "AGENT_SYSTEM_PROMPT",
    "format_context_for_rag",
    "format_papers_for_review",
]
