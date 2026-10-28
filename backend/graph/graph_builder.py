"""NetworkX directed graph topology builder and Cytoscape.js serializer with prompt-activated relevance."""

import re
from typing import Any, Dict, List, Optional, Set
import networkx as nx

from backend.graph.entity_miner import entity_miner
from backend.models.graph import (
    CytoscapeEdge,
    CytoscapeEdgeData,
    CytoscapeElements,
    CytoscapeNode,
    CytoscapeNodeData,
    GraphResponse,
)
from backend.models.paper import PaperMetadata, TextChunk
from backend.rag.bm25_index import tokenize_scientific_text

NODE_COLORS: Dict[str, str] = {
    "Paper": "#38BDF8",    # Sky Blue
    "Author": "#A78BFA",   # Violet
    "Method": "#34D399",   # Emerald
    "Dataset": "#FBBF24",  # Amber
    "Metric": "#F472B6",   # Pink
}


def _slugify_id(prefix: str, label: str) -> str:
    """Create a deterministic, Cytoscape-safe node ID from an entity type prefix and label."""
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return f"node_{prefix.lower()}_{slug}"


def _prioritize_entities(candidates: List[str], priority_text: str, max_count: int) -> List[str]:
    """Prioritize entities that appear in the paper title/abstract to keep the graph high-signal."""
    if len(candidates) <= max_count:
        return candidates
    pt_lower = priority_text.lower()
    scored = sorted(
        candidates,
        key=lambda item: (1 if item.lower() in pt_lower else 0, -len(item)),
        reverse=True,
    )
    return scored[:max_count]


class KnowledgeGraphBuilder:
    """Builds a NetworkX DiGraph over ingested papers and serializes to Cytoscape.js format."""

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()

    def build_graph(
        self,
        papers: List[PaperMetadata],
        chunks_by_paper: Dict[str, List[TextChunk]],
    ) -> nx.DiGraph:
        """Construct a directed knowledge graph of Papers, Authors, Methods, Datasets, and Metrics."""
        g = nx.DiGraph()
        known_paper_ids = {p.id for p in papers}
        mined_by_paper: Dict[str, Dict[str, Any]] = {}

        # First pass: extract entities and create Paper nodes with rich metadata
        for paper in papers:
            p_chunks = chunks_by_paper.get(paper.id, [])
            mined = entity_miner.extract_for_paper(paper, p_chunks)
            mined_by_paper[paper.id] = mined

            paper_node_id = f"node_{paper.id}"
            g.add_node(
                paper_node_id,
                label=paper.title,
                type="Paper",
                color=NODE_COLORS["Paper"],
                metadata={
                    "paper_id": paper.id,
                    "year": paper.year,
                    "authors": paper.authors,
                    "doi": paper.doi,
                    "total_pages": paper.total_pages,
                    "methods": mined["methods"],
                    "datasets": mined["datasets"],
                    "metrics": mined["metrics"],
                },
            )

        # Second pass: add high-signal Author, Method, Dataset, Metric nodes + typed edges
        for paper in papers:
            paper_node_id = f"node_{paper.id}"
            mined = mined_by_paper[paper.id]
            priority_context = f"{paper.title} {paper.abstract or ''}"

            # Lead Authors (up to 2 per paper)
            for author_name in mined["authors"][:2]:
                author_node_id = _slugify_id("author", author_name)
                if not g.has_node(author_node_id):
                    g.add_node(
                        author_node_id,
                        label=author_name,
                        type="Author",
                        color=NODE_COLORS["Author"],
                        metadata={"papers": [paper.id]},
                    )
                else:
                    papers_list = g.nodes[author_node_id]["metadata"].setdefault("papers", [])
                    if paper.id not in papers_list:
                        papers_list.append(paper.id)

                g.add_edge(
                    author_node_id,
                    paper_node_id,
                    type="AUTHORED",
                    label="AUTHORED",
                    weight=1.0,
                )

            # Top signature Methods per paper (up to 3) -> Paper PROPOSES Method
            top_methods = _prioritize_entities(mined["methods"], priority_context, max_count=3)
            for method_name in top_methods:
                method_node_id = _slugify_id("method", method_name)
                if not g.has_node(method_node_id):
                    g.add_node(
                        method_node_id,
                        label=method_name,
                        type="Method",
                        color=NODE_COLORS["Method"],
                        metadata={"papers": [paper.id]},
                    )
                else:
                    papers_list = g.nodes[method_node_id]["metadata"].setdefault("papers", [])
                    if paper.id not in papers_list:
                        papers_list.append(paper.id)

                g.add_edge(
                    paper_node_id,
                    method_node_id,
                    type="PROPOSES",
                    label="PROPOSES",
                    weight=1.5,
                )

            # Top Datasets per paper (up to 2) -> Paper EVALUATES_ON Dataset
            top_datasets = _prioritize_entities(mined["datasets"], priority_context, max_count=2)
            for dataset_name in top_datasets:
                dataset_node_id = _slugify_id("dataset", dataset_name)
                if not g.has_node(dataset_node_id):
                    g.add_node(
                        dataset_node_id,
                        label=dataset_name,
                        type="Dataset",
                        color=NODE_COLORS["Dataset"],
                        metadata={"papers": [paper.id]},
                    )
                else:
                    papers_list = g.nodes[dataset_node_id]["metadata"].setdefault("papers", [])
                    if paper.id not in papers_list:
                        papers_list.append(paper.id)

                g.add_edge(
                    paper_node_id,
                    dataset_node_id,
                    type="EVALUATES_ON",
                    label="EVALUATES_ON",
                    weight=1.2,
                )

            # Top Metrics per paper (up to 2) -> Paper ACHIEVES Metric
            top_metrics = _prioritize_entities(mined["metrics"], priority_context, max_count=2)
            for metric_name in top_metrics:
                metric_node_id = _slugify_id("metric", metric_name)
                if not g.has_node(metric_node_id):
                    g.add_node(
                        metric_node_id,
                        label=metric_name,
                        type="Metric",
                        color=NODE_COLORS["Metric"],
                        metadata={"papers": [paper.id]},
                    )
                else:
                    papers_list = g.nodes[metric_node_id]["metadata"].setdefault("papers", [])
                    if paper.id not in papers_list:
                        papers_list.append(paper.id)

                g.add_edge(
                    paper_node_id,
                    metric_node_id,
                    type="ACHIEVES",
                    label="ACHIEVES",
                    weight=1.0,
                )

            # Cross-paper CITES edges
            for cited_pid in mined["cited_paper_ids"]:
                if cited_pid in known_paper_ids and cited_pid != paper.id:
                    target_paper_node = f"node_{cited_pid}"
                    g.add_edge(
                        paper_node_id,
                        target_paper_node,
                        type="CITES",
                        label="CITES",
                        weight=2.0,
                    )

        self.graph = g
        return g

    def to_cytoscape(
        self,
        entity_type: Optional[str] = None,
        min_degree: int = 1,
        query: Optional[str] = None,
        active_chunk_ids: Optional[List[str]] = None,
        all_chunks: Optional[List[TextChunk]] = None,
    ) -> GraphResponse:
        """Serialize the NetworkX DiGraph into CytoscapeResponse with optional query-active highlighting."""
        g = self.graph
        degrees = dict(g.degree())

        kept_node_ids: Set[str] = set()
        for node_id, attrs in g.nodes(data=True):
            deg = degrees.get(node_id, 0)
            if deg < min_degree:
                continue
            if entity_type and attrs.get("type") != entity_type:
                continue
            kept_node_ids.add(node_id)

        has_active_prompt = bool((query and query.strip()) or active_chunk_ids)
        node_relevance: Dict[str, float] = {}
        active_node_ids: Set[str] = set()

        if has_active_prompt:
            query_tokens = set(tokenize_scientific_text(query or ""))
            cited_paper_ids: Set[str] = set()
            chunk_text_by_id: Dict[str, TextChunk] = {
                c.id: c for c in (all_chunks or [])
            }
            active_chunks_text = ""

            for cid in active_chunk_ids or []:
                if cid in chunk_text_by_id:
                    ch = chunk_text_by_id[cid]
                    cited_paper_ids.add(ch.paper_id)
                    active_chunks_text += " " + ch.text
                else:
                    m = re.match(r"^(paper_[a-zA-Z0-9]+)_c\d+$", cid)
                    if m:
                        cited_paper_ids.add(m.group(1))

            active_extracted = entity_miner.extract_from_text(
                f"{query or ''} {active_chunks_text}"
            )
            matched_entities = set(
                active_extracted["methods"]
                + active_extracted["datasets"]
                + active_extracted["metrics"]
            )

            for node_id in kept_node_ids:
                attrs = g.nodes[node_id]
                label = str(attrs.get("label", ""))
                ntype = str(attrs.get("type", ""))
                meta = attrs.get("metadata", {})
                label_tokens = set(tokenize_scientific_text(label))

                score = 0.15
                if ntype == "Paper" and meta.get("paper_id") in cited_paper_ids:
                    score = max(score, 0.95)
                if label in matched_entities:
                    score = max(score, 0.92)
                if query_tokens and label_tokens:
                    overlap = len(query_tokens.intersection(label_tokens))
                    if overlap > 0:
                        score = max(score, min(0.95, 0.72 + 0.10 * overlap))
                node_papers = set(meta.get("papers", []))
                if node_papers.intersection(cited_paper_ids) and label.lower() in active_chunks_text.lower():
                    score = max(score, 0.85)

                node_relevance[node_id] = round(score, 3)
                if score >= 0.70:
                    active_node_ids.add(node_id)

            bridge_candidates: Set[str] = set()
            undirected = g.to_undirected()
            for nid in kept_node_ids:
                if nid in active_node_ids:
                    continue
                neighbors = set(undirected.neighbors(nid))
                if len(neighbors.intersection(active_node_ids)) >= 2:
                    bridge_candidates.add(nid)
                    node_relevance[nid] = 0.76
            active_node_ids.update(bridge_candidates)

        cy_nodes: List[CytoscapeNode] = []
        for node_id in sorted(kept_node_ids):
            attrs = g.nodes[node_id]
            rel_score = node_relevance.get(node_id) if has_active_prompt else None
            is_dimmed = bool(has_active_prompt and active_node_ids and node_id not in active_node_ids)
            cy_nodes.append(
                CytoscapeNode(
                    data=CytoscapeNodeData(
                        id=node_id,
                        label=attrs["label"],
                        type=attrs["type"],
                        color=attrs["color"],
                        degree=degrees.get(node_id, 1),
                        relevance_score=rel_score,
                        is_dimmed=is_dimmed,
                        metadata=attrs.get("metadata", {}),
                    )
                )
            )

        cy_edges: List[CytoscapeEdge] = []
        edge_idx = 1
        for u, v, eattrs in g.edges(data=True):
            if u not in kept_node_ids or v not in kept_node_ids:
                continue
            is_edge_active = bool(
                has_active_prompt and u in active_node_ids and v in active_node_ids
            )
            is_edge_dimmed = bool(
                has_active_prompt and active_node_ids and not is_edge_active
            )
            cy_edges.append(
                CytoscapeEdge(
                    data=CytoscapeEdgeData(
                        id=f"edge_{edge_idx}",
                        source=u,
                        target=v,
                        type=eattrs["type"],
                        label=eattrs["label"],
                        weight=float(eattrs.get("weight", 1.0)),
                        is_active=is_edge_active,
                        is_dimmed=is_edge_dimmed,
                    )
                )
            )
            edge_idx += 1

        return GraphResponse(
            elements=CytoscapeElements(nodes=cy_nodes, edges=cy_edges),
            total_nodes=len(cy_nodes),
            total_edges=len(cy_edges),
        )


graph_builder = KnowledgeGraphBuilder()
