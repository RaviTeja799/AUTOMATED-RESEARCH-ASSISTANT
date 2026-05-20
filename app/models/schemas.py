"""
Pydantic models for request/response validation.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Paper Models
# ============================================================================

class PaperMetadata(BaseModel):
    """Metadata extracted from a paper."""
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    num_pages: Optional[int] = None


class PaperUploadResponse(BaseModel):
    """Response after uploading a paper."""
    paper_id: str
    filename: str
    status: str
    message: str
    metadata: Optional[PaperMetadata] = None
    num_chunks: Optional[int] = None
    processing_time: Optional[float] = None


class PaperInfo(BaseModel):
    """Information about a stored paper."""
    paper_id: str
    filename: str
    metadata: PaperMetadata
    upload_date: Optional[str] = None
    num_chunks: int
    sections: List[str] = Field(default_factory=list)
    file_size_bytes: Optional[int] = None


# ============================================================================
# Query Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request for querying papers."""
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None
    include_citations: bool = Field(default=True)
    
    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate and clean question."""
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        return v


class Citation(BaseModel):
    """Citation information for a source."""
    paper_id: str
    paper_title: str
    authors: List[str]
    chunk_id: str
    page_number: Optional[int] = None
    relevance_score: float
    text_snippet: str


class QueryResponse(BaseModel):
    """Response to a query."""
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    confidence: Optional[float] = None
    processing_time: float
    retrieved_chunks: int


# ============================================================================
# Summarization Models
# ============================================================================

class SummarizeRequest(BaseModel):
    """Request for paper summarization."""
    paper_id: str
    summary_type: str = Field(
        default="comprehensive",
        pattern="^(brief|comprehensive|technical)$"
    )
    max_length: Optional[int] = Field(default=500, ge=100, le=2000)


class PaperSummary(BaseModel):
    """Summary of a paper."""
    paper_id: str
    paper_title: str
    summary: str
    key_findings: List[str] = Field(default_factory=list)
    methodology: Optional[str] = None
    limitations: Optional[str] = None
    summary_type: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Literature Review Models
# ============================================================================

class LiteratureReviewRequest(BaseModel):
    """Request for literature review generation."""
    topic: str = Field(..., min_length=3, max_length=500)
    max_papers: int = Field(default=10, ge=1, le=50)
    focus_areas: Optional[List[str]] = None
    date_range: Optional[Dict[str, str]] = None


class PaperSummaryBrief(BaseModel):
    """Brief summary for literature review."""
    paper_id: str
    title: str
    authors: List[str]
    year: Optional[str] = None
    key_contribution: str
    relevance_score: float


class LiteratureReview(BaseModel):
    """Generated literature review."""
    topic: str
    overview: str
    papers_reviewed: List[PaperSummaryBrief]
    key_themes: List[str]
    research_gaps: List[str]
    future_directions: List[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    num_papers: int


# ============================================================================
# Chunk Models
# ============================================================================

class DocumentChunk(BaseModel):
    """A chunk of text from a document."""
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    paper_id: str
    text: str
    section: Optional[str] = None
    page_number: Optional[int] = None
    chunk_index: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Health and Status Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    qdrant_connected: bool
    groq_available: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Agent Models
# ============================================================================

class AgentAction(BaseModel):
    """Action taken by an agent."""
    action_type: str
    tool_name: str
    tool_input: Dict[str, Any]
    result: Optional[str] = None


class AgentResponse(BaseModel):
    """Response from agent execution."""
    final_answer: str
    actions_taken: List[AgentAction] = Field(default_factory=list)
    reasoning: Optional[str] = None
    processing_time: float
