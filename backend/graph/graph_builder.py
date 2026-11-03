"""NetworkX directed graph topology builder and Cytoscape.js serializer with node explanations."""

import re
from typing import Any, Dict, List, Optional, Set
import networkx as nx

from backend.graph.entity_miner import (
    entity_miner,
    find_citation_occurrences_in_paper,
    find_entity_evidence_in_paper,
    get_entity_description,
)
from backend.graph.topic_clustering import compute_paper_hierarchy
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
        """Construct a directed knowledge graph with rich node explanations and per-paper relations."""
        g = nx.DiGraph()
        known_paper_ids = {p.id for p in papers}
        papers_by_id = {p.id: p for p in papers}
        mined_by_paper: Dict[str, Dict[str, Any]] = {}

        # First pass: extract entities and compute hierarchical topic/citation groups
        for paper in papers:
            p_chunks = chunks_by_paper.get(paper.id, [])
            mined = entity_miner.extract_for_paper(paper, p_chunks)
            mined_by_paper[paper.id] = mined

        hierarchy = compute_paper_hierarchy(papers, chunks_by_paper, mined_by_paper)
        paper_assignments = hierarchy["paper_assignments"]

        for paper in papers:
            p_chunks = chunks_by_paper.get(paper.id, [])
            mined = mined_by_paper[paper.id]
            assign = paper_assignments.get(paper.id, {})

            summary_text = paper.abstract or (p_chunks[0].text if p_chunks else paper.title)
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
                    "description": summary_text,
                    "methods": mined["methods"],
                    "datasets": mined["datasets"],
                    "metrics": mined["metrics"],
                    "group_id": assign.get("group_id", "group_1"),
                    "group_label": assign.get("group_label", "Research Literature"),
                    "group_details": assign.get("group_details"),
                    "subgroup_id": assign.get("subgroup_id"),
                    "subgroup_label": assign.get("subgroup_label"),
                    "subgroup_details": assign.get("subgroup_details"),
                    "paper_relations": [],
                },
            )

        def _register_entity_node(
            node_id: str,
            label: str,
            entity_type: str,
            paper: PaperMetadata,
            p_chunks: List[TextChunk],
        ) -> Dict[str, Any]:
            evidence = find_entity_evidence_in_paper(label, paper, p_chunks)
            if not g.has_node(node_id):
                g.add_node(
                    node_id,
                    label=label,
                    type=entity_type,
                    color=NODE_COLORS[entity_type],
                    metadata={
                        "description": get_entity_description(label, entity_type),
                        "papers": [paper.id],
                        "paper_relations": [evidence],
                    },
                )
            else:
                meta = g.nodes[node_id]["metadata"]
                papers_list = meta.setdefault("papers", [])
                if paper.id not in papers_list:
                    papers_list.append(paper.id)
                rel_list = meta.setdefault("paper_relations", [])
                if not any(r["paper_id"] == paper.id for r in rel_list):
                    rel_list.append(evidence)
            return evidence

        # Second pass: add Author, Method, Dataset, Metric nodes + typed edges + per-paper relation evidence
        for paper in papers:
            paper_node_id = f"node_{paper.id}"
            p_chunks = chunks_by_paper.get(paper.id, [])
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
                        metadata={
                            "description": get_entity_description(author_name, "Author"),
                            "papers": [paper.id],
                            "paper_relations": [
                                {
                                    "paper_id": paper.id,
                                    "paper_title": paper.title,
                                    "year": paper.year,
                                    "role": "Co-Author",
                                    "explanation": paper.abstract or f"Authored {paper.title}.",
                                    "page": 1,
                                }
                            ],
                        },
                    )
                else:
                    meta = g.nodes[author_node_id]["metadata"]
                    if paper.id not in meta["papers"]:
                        meta["papers"].append(paper.id)
                        meta["paper_relations"].append(
                            {
                                "paper_id": paper.id,
                                "paper_title": paper.title,
                                "year": paper.year,
                                "role": "Co-Author",
                                "explanation": paper.abstract or f"Authored {paper.title}.",
                                "page": 1,
                            }
                        )

                g.add_edge(
                    author_node_id,
                    paper_node_id,
                    type="AUTHORED",
                    label="AUTHORED",
                    weight=1.0,
                )

            # Top signature Methods per paper (up to 3)
            top_methods = _prioritize_entities(mined["methods"], priority_context, max_count=3)
            for method_name in top_methods:
                method_node_id = _slugify_id("method", method_name)
                evidence = _register_entity_node(
                    method_node_id, method_name, "Method", paper, p_chunks
                )
                edge_label = (
                    "PROPOSES"
                    if evidence["role"] == "Introduces / Proposes"
                    else "BUILDS ON"
                )
                g.add_edge(
                    paper_node_id,
                    method_node_id,
                    type="PROPOSES",
                    label=edge_label,
                    weight=1.5,
                )

            # Top Datasets per paper (up to 2)
            top_datasets = _prioritize_entities(mined["datasets"], priority_context, max_count=2)
            for dataset_name in top_datasets:
                dataset_node_id = _slugify_id("dataset", dataset_name)
                _register_entity_node(
                    dataset_node_id, dataset_name, "Dataset", paper, p_chunks
                )
                g.add_edge(
                    paper_node_id,
                    dataset_node_id,
                    type="EVALUATES_ON",
                    label="EVALUATES_ON",
                    weight=1.2,
                )

            # Top Metrics per paper (up to 2)
            top_metrics = _prioritize_entities(mined["metrics"], priority_context, max_count=2)
            for metric_name in top_metrics:
                metric_node_id = _slugify_id("metric", metric_name)
                _register_entity_node(
                    metric_node_id, metric_name, "Metric", paper, p_chunks
                )
                g.add_edge(
                    paper_node_id,
                    metric_node_id,
                    type="ACHIEVES",
                    label="ACHIEVES",
                    weight=1.0,
                )

            # Cross-paper CITES edges + populate Paper node's paper_relations with exact occurrences
            candidate_cited_ids = set(mined["cited_paper_ids"]) | known_paper_ids
            for cited_pid in sorted(candidate_cited_ids):
                if cited_pid not in known_paper_ids or cited_pid == paper.id:
                    continue
                cited_paper = papers_by_id[cited_pid]

                occurrences = find_citation_occurrences_in_paper(
                    paper, cited_paper, p_chunks
                )
                if not occurrences and cited_pid in mined["cited_paper_ids"]:
                    first_chunk = p_chunks[0] if p_chunks else None
                    occurrences = [
                        {
                            "chunk_id": first_chunk.id if first_chunk else f"{paper.id}_c0",
                            "paper_id": paper.id,
                            "paper_title": paper.title,
                            "cited_paper_id": cited_paper.id,
                            "cited_paper_title": cited_paper.title,
                            "page": first_chunk.page_number if first_chunk else 1,
                            "section": first_chunk.section if first_chunk else "Introduction",
                            "bbox": (
                                first_chunk.bbox.model_dump()
                                if first_chunk and hasattr(first_chunk.bbox, "model_dump")
                                else None
                            ),
                            "snippet": f"{paper.title} cites and builds upon {cited_paper.title}.",
                        }
                    ]

                if not occurrences:
                    continue

                is_preprint_anomaly = bool(
                    paper.year
                    and cited_paper.year
                    and int(paper.year) < int(cited_paper.year)
                )
                anomaly_note = (
                    f"This {paper.year} paper cites a work dated {cited_paper.year}. "
                    "In academic publishing, this occurs when a paper cites an earlier arXiv preprint "
                    "or working paper before its formal conference/journal publication year, or when "
                    "the citing paper was updated in a later arXiv revision (v2/v3) while keeping its initial year."
                    if is_preprint_anomaly
                    else None
                )

                target_paper_node = f"node_{cited_pid}"
                first_occ = occurrences[0]
                base_label = f"Cites ({len(occurrences)})" if len(occurrences) > 1 else "Cites"
                edge_label = f"{base_label} ⚠" if is_preprint_anomaly else base_label

                g.add_edge(
                    paper_node_id,
                    target_paper_node,
                    type="CITES",
                    label=edge_label,
                    weight=2.0,
                    metadata={
                        "citing_paper_id": paper.id,
                        "citing_paper_title": paper.title,
                        "citing_year": paper.year,
                        "cited_paper_id": cited_paper.id,
                        "cited_paper_title": cited_paper.title,
                        "cited_year": cited_paper.year,
                        "citation_count": len(occurrences),
                        "is_preprint_anomaly": is_preprint_anomaly,
                        "anomaly_note": anomaly_note,
                        "citations": occurrences,
                    },
                )
                g.nodes[paper_node_id]["metadata"]["paper_relations"].append(
                    {
                        "paper_id": paper.id,
                        "target_paper_id": cited_paper.id,
                        "paper_title": cited_paper.title,
                        "year": cited_paper.year,
                        "role": f"Cites ({len(occurrences)}x)" + (" · Preprint/Revision" if is_preprint_anomaly else ""),
                        "is_preprint_anomaly": is_preprint_anomaly,
                        "anomaly_note": anomaly_note,
                        "explanation": first_occ["snippet"],
                        "page": first_occ["page"],
                        "bbox": first_occ["bbox"],
                        "section": first_occ["section"],
                        "citations": occurrences,
                    }
                )
                g.nodes[target_paper_node]["metadata"]["paper_relations"].append(
                    {
                        "paper_id": paper.id,
                        "target_paper_id": cited_paper.id,
                        "paper_title": paper.title,
                        "year": paper.year,
                        "role": f"Cited By ({len(occurrences)}x)" + (" · Preprint/Revision" if is_preprint_anomaly else ""),
                        "is_preprint_anomaly": is_preprint_anomaly,
                        "anomaly_note": anomaly_note,
                        "explanation": first_occ["snippet"],
                        "page": first_occ["page"],
                        "bbox": first_occ["bbox"],
                        "section": first_occ["section"],
                        "citations": occurrences,
                    }
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
            # Generic words that must never light up a node on their own (e.g. "models" matching
            # "LoRA: ... Large Language Models" when the question is about Cucker-Smale models)
            generic_tokens = {
                "model", "models", "method", "methods", "approach", "approaches", "result", "results",
                "large", "language", "system", "systems", "study", "analysis", "theory", "new",
                "based", "learning", "network", "networks", "data", "paper", "papers", "three",
                "two", "one", "four", "five", "first", "second", "third", "version", "versions",
                "variant", "variants", "work", "works", "show", "find", "provide", "information",
            }
            query_tokens = {
                t for t in tokenize_scientific_text(query or "")
                if t not in generic_tokens and not t.isdigit() and len(t) >= 3
            }
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
                    m = re.match(r"^(paper_.+)_c\d+$", cid)
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
                node_papers = set(meta.get("papers", []))
                is_cited_paper = ntype == "Paper" and meta.get("paper_id") in cited_paper_ids
                linked_to_cited = bool(node_papers.intersection(cited_paper_ids))
                if is_cited_paper:
                    score = max(score, 0.95)
                if label in matched_entities and (not cited_paper_ids or linked_to_cited or is_cited_paper):
                    score = max(score, 0.92)
                if query_tokens and label_tokens:
                    overlap = len(query_tokens.intersection(label_tokens))
                    # When the answer cites papers, only those papers (and their entities) may
                    # light up via keyword overlap; otherwise unrelated nodes get highlighted.
                    allowed = (not cited_paper_ids) or is_cited_paper or linked_to_cited
                    if overlap > 0 and allowed:
                        score = max(score, min(0.95, 0.72 + 0.10 * overlap))
                if linked_to_cited and label.lower() in active_chunks_text.lower():
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
                        metadata=eattrs.get("metadata", {}),
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
