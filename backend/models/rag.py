"""Pydantic v2 request and response models for Hybrid RAG retrieval and grounded synthesis."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from backend.models.paper import BoundingBox


class CitationToken(BaseModel):
    """Provenance citation token linking an answer claim to an exact PDF page and bounding box."""

    paper_id: str = Field(..., min_length=1, description="Source paper identifier")
    paper_title: str = Field(..., min_length=1, description="Source paper title")
    page: int = Field(..., ge=1, description="1-indexed page number in PDF")
    bbox: BoundingBox = Field(..., description="Normalized spatial bounding box [page, x, y, width, height]")
    chunk_id: str = Field(..., min_length=1, description="Unique source chunk identifier")
    section: str = Field(default="Body", description="Section title in the paper")
    snippet: str = Field(default="", description="Verbatim excerpt from the source chunk")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Normalized relevance confidence score [0.0 - 1.0]")


class QueryRequest(BaseModel):
    """Client query payload for multi-document comparative Q&A."""

    query: str = Field(..., min_length=3, max_length=1000, description="Natural language scientific question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top re-ranked passages passed to synthesis")
    paper_ids: Optional[List[str]] = Field(default=None, description="Optional subset of paper IDs to search")
    api_key: Optional[str] = Field(default=None, description="Optional user-supplied Gemini API key override")


class QueryResponse(BaseModel):
    """Grounded synthesis response with clickable spatial citation tokens and latency telemetry."""

    query: str
    answer: str
    status: Literal["success", "insufficient_context"] = Field(
        ..., description="'success' when grounded in retrieved chunks, 'insufficient_context' when refused"
    )
    citations: List[CitationToken] = Field(default_factory=list)
    model_used: str = Field(
        ..., description="Model or guardrail identifier (e.g., 'gemini-2.0-flash', 'extractive-fallback', 'deterministic-guardrail')"
    )
    retrieval_latency_ms: float = Field(..., ge=0.0)
    synthesis_latency_ms: float = Field(..., ge=0.0)

