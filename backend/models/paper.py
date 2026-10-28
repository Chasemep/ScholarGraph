"""Pydantic v2 domain models for documents, spatial bounding boxes, and text chunks."""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class BoundingBox(BaseModel):
    """Normalized page-relative spatial bounding box [page, x, y, width, height]."""

    page: int = Field(..., ge=1, description="1-indexed page number")
    x: float = Field(..., ge=0.0, le=1.0, description="Normalized horizontal coordinate [0.0 - 1.0]")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalized vertical coordinate [0.0 - 1.0]")
    width: float = Field(..., gt=0.0, le=1.0, description="Normalized width (0.0 - 1.0]")
    height: float = Field(..., gt=0.0, le=1.0, description="Normalized height (0.0 - 1.0]")

    def to_list(self) -> List[float | int]:
        """Return coordinates as [page, x, y, width, height]."""
        return [self.page, self.x, self.y, self.width, self.height]


class PaperMetadata(BaseModel):
    """Bibliographic and file metadata for an ingested scientific paper."""

    id: str = Field(..., min_length=1, description="Unique paper identifier (e.g. paper_vaswani2017)")
    title: str = Field(..., min_length=1, description="Full title of the scientific paper")
    authors: List[str] = Field(default_factory=list, description="Ordered list of author names")
    year: Optional[int] = Field(default=None, ge=1900, le=2100, description="Publication year")
    abstract: Optional[str] = Field(default=None, description="Extracted abstract text")
    doi: Optional[str] = Field(default=None, description="Digital Object Identifier")
    filepath: str = Field(..., min_length=1, description="Relative path to stored PDF file")
    total_pages: int = Field(..., ge=1, description="Total page count in PDF")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Ingestion timestamp (UTC)",
    )

    @field_validator("title")
    @classmethod
    def strip_and_validate_title(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Paper title cannot be empty or whitespace-only")
        return cleaned


class TextChunk(BaseModel):
    """Section-segmented text passage with spatial bounding-box provenance."""

    id: str = Field(..., min_length=1, description="Unique chunk identifier ({paper_id}_c{index})")
    paper_id: str = Field(..., min_length=1, description="Parent paper identifier")
    paper_title: Optional[str] = Field(default=None, description="Parent paper title for citation display")
    section: str = Field(default="Body", min_length=1, description="Section heading (Abstract, Methods, etc.)")
    page_number: int = Field(..., ge=1, description="1-indexed page number")
    bbox: BoundingBox = Field(..., description="Normalized bounding box for highlight synchronization")
    text: str = Field(..., min_length=1, description="Cleaned chunk text content")
    token_count: int = Field(..., ge=1, description="Approximate word/token count")

    @field_validator("text")
    @classmethod
    def validate_non_empty_text(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Chunk text cannot be empty or whitespace-only")
        return cleaned


class IngestionStatus(BaseModel):
    """Lifecycle status tracking for asynchronous PDF ingestion tasks."""

    task_id: str = Field(..., min_length=1)
    paper_id: Optional[str] = Field(default=None)
    filename: str = Field(..., min_length=1)
    status: Literal["uploading", "parsing", "embedding", "ready", "failed"] = Field(
        ..., description="Current ingestion stage"
    )
    progress_percentage: int = Field(..., ge=0, le=100)
    error_message: Optional[str] = Field(default=None)

