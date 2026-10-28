"""Cytoscape.js-compliant Pydantic v2 serialization schemas for the Knowledge Graph."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

EntityType = Literal["Paper", "Author", "Method", "Dataset", "Metric"]
EdgeRelationType = Literal["AUTHORED", "PROPOSES", "EVALUATES_ON", "CITES", "ACHIEVES"]


class CytoscapeNodeData(BaseModel):
    """Data payload for a single Cytoscape.js node."""

    id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    type: EntityType = Field(..., description="'Paper' | 'Author' | 'Method' | 'Dataset' | 'Metric'")
    color: str = Field(..., description="Hex color code for node category")
    degree: int = Field(default=1, ge=0, description="Total undirected connection degree")
    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Dynamic prompt relevance score [0.0 - 1.0] when query-active",
    )
    is_dimmed: bool = Field(
        default=False,
        description="True when a query is active and this node is peripheral (20% opacity)",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CytoscapeNode(BaseModel):
    """Wrapper for a Cytoscape.js node element."""

    data: CytoscapeNodeData


class CytoscapeEdgeData(BaseModel):
    """Data payload for a single directed Cytoscape.js edge."""

    id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    type: EdgeRelationType = Field(
        ..., description="'AUTHORED' | 'PROPOSES' | 'EVALUATES_ON' | 'CITES' | 'ACHIEVES'"
    )
    label: str = Field(..., min_length=1)
    weight: float = Field(default=1.0, gt=0.0)
    is_active: bool = Field(
        default=False,
        description="True when edge connects active relevant nodes (4px luminous stroke)",
    )
    is_dimmed: bool = Field(
        default=False,
        description="True when edge is non-relevant during an active query (20% opacity)",
    )


class CytoscapeEdge(BaseModel):
    """Wrapper for a Cytoscape.js edge element."""

    data: CytoscapeEdgeData


class CytoscapeElements(BaseModel):
    """Container holding Cytoscape node and edge arrays."""

    nodes: List[CytoscapeNode] = Field(default_factory=list)
    edges: List[CytoscapeEdge] = Field(default_factory=list)


class GraphResponse(BaseModel):
    """Complete Knowledge Graph API response payload."""

    elements: CytoscapeElements
    total_nodes: int = Field(..., ge=0)
    total_edges: int = Field(..., ge=0)


class GraphHighlightRequest(BaseModel):
    """Request payload for POST /api/graph/highlight to compute dynamic relevance scaling."""

    query: str = Field(default="", description="Active user search prompt or question")
    active_chunk_ids: List[str] = Field(
        default_factory=list,
        description="Chunk IDs cited in the active RAG synthesis response",
    )
    paper_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional filter restricting graph to specific paper IDs",
    )

