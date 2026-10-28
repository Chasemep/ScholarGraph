"""FastAPI routes for the Knowledge Graph subsystem (GET /api/graph and POST /api/graph/highlight)."""

from typing import Dict, List, Optional
from fastapi import APIRouter, Query

from backend.api.query_routes import ensure_corpus_indexed
from backend.graph.graph_builder import graph_builder
from backend.models.graph import GraphHighlightRequest, GraphResponse
from backend.models.paper import PaperMetadata, TextChunk
from backend.storage.db import db

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])


def _rebuild_graph_from_db(paper_ids: Optional[List[str]] = None) -> List[TextChunk]:
    """Synchronize the NetworkX knowledge graph with the current SQLite papers and chunks."""
    ensure_corpus_indexed()
    papers: List[PaperMetadata] = db.list_papers()
    if paper_ids:
        allowed = set(paper_ids)
        papers = [p for p in papers if p.id in allowed]

    all_chunks = db.get_all_chunks(paper_ids=paper_ids)
    chunks_by_paper: Dict[str, List[TextChunk]] = {}
    for ch in all_chunks:
        chunks_by_paper.setdefault(ch.paper_id, []).append(ch)

    graph_builder.build_graph(papers, chunks_by_paper)
    return all_chunks


@router.get("", response_model=GraphResponse)
async def get_knowledge_graph(
    entity_type: Optional[str] = Query(
        default=None,
        description="Optional filter by 'Paper', 'Author', 'Method', 'Dataset', or 'Metric'",
    ),
    min_degree: int = Query(
        default=1,
        ge=0,
        description="Minimum node degree threshold",
    ),
) -> GraphResponse:
    """Return the complete Cytoscape-compliant JSON topology of all ingested papers and entities."""
    _rebuild_graph_from_db()
    return graph_builder.to_cytoscape(
        entity_type=entity_type,
        min_degree=min_degree,
    )


@router.post("/highlight", response_model=GraphResponse)
async def highlight_knowledge_graph(request: GraphHighlightRequest) -> GraphResponse:
    """Compute prompt-activated node relevance scaling, 4px active edges, and 20% peripheral dimming."""
    all_chunks = _rebuild_graph_from_db(paper_ids=request.paper_ids)
    return graph_builder.to_cytoscape(
        min_degree=1,
        query=request.query,
        active_chunk_ids=request.active_chunk_ids,
        all_chunks=all_chunks,
    )

