"""Automated unit and integration tests for Knowledge Graph mining, NetworkX topology,
Cytoscape serialization, and prompt-activated relevance dynamics (T023).
"""

from fastapi.testclient import TestClient

from backend.graph.entity_miner import ScientificEntityMiner
from backend.graph.graph_builder import KnowledgeGraphBuilder
from backend.main import app
from backend.models.paper import BoundingBox, PaperMetadata, TextChunk


def _sample_papers_and_chunks():
    p_vaswani = PaperMetadata(
        id="paper_vaswani2017",
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer"],
        year=2017,
        abstract="We propose the Transformer based on Self-Attention and Multi-Head Attention.",
        filepath="data/papers/vaswani2017_attention.pdf",
        total_pages=3,
    )
    p_lora = PaperMetadata(
        id="paper_hu2021",
        title="LoRA: Low-Rank Adaptation of Large Language Models",
        authors=["Edward J. Hu", "Yelong Shen"],
        year=2021,
        abstract="We propose LoRA for parameter efficiency, reducing GPU memory on Transformer models.",
        filepath="data/papers/hu2021_lora.pdf",
        total_pages=3,
    )

    chunks_by_paper = {
        "paper_vaswani2017": [
            TextChunk(
                id="paper_vaswani2017_c0",
                paper_id="paper_vaswani2017",
                paper_title=p_vaswani.title,
                section="Experiments",
                page_number=3,
                bbox=BoundingBox(page=3, x=0.1, y=0.2, width=0.8, height=0.15),
                text="Our Transformer model achieves 28.4 BLEU on the WMT 2014 translation task using Scaled Dot-Product Attention.",
                token_count=17,
            )
        ],
        "paper_hu2021": [
            TextChunk(
                id="paper_hu2021_c0",
                paper_id="paper_hu2021",
                paper_title=p_lora.title,
                section="Experiments",
                page_number=3,
                bbox=BoundingBox(page=3, x=0.1, y=0.3, width=0.8, height=0.15),
                text="Following Vaswani et al. (2017), we apply LoRA and Low-Rank Decomposition to Self-Attention on GLUE and WikiSQL, achieving 91.7% accuracy with 10,000 times fewer trainable parameters.",
                token_count=27,
            )
        ],
    }
    return [p_vaswani, p_lora], chunks_by_paper


def test_entity_miner_extracts_methods_datasets_metrics_and_citations():
    """Verify ScientificEntityMiner extracts canonical entities, custom patterns, and citation cues."""
    miner = ScientificEntityMiner(use_spacy_ner=True)
    papers, chunks_by_paper = _sample_papers_and_chunks()

    lora_entities = miner.extract_for_paper(papers[1], chunks_by_paper["paper_hu2021"])
    assert "LoRA" in lora_entities["methods"]
    assert "Self-Attention" in lora_entities["methods"]
    assert "Low-Rank Decomposition" in lora_entities["methods"]
    assert "GLUE" in lora_entities["datasets"]
    assert "WikiSQL" in lora_entities["datasets"]
    assert "Accuracy" in lora_entities["metrics"]
    assert "Parameter Efficiency" in lora_entities["metrics"]
    assert "paper_vaswani2017" in lora_entities["cited_paper_ids"]
    # Edge case: paper must never cite itself
    assert "paper_hu2021" not in lora_entities["cited_paper_ids"]

    # Edge case: empty or whitespace input returns empty lists
    empty_res = miner.extract_from_text("   ")
    assert empty_res == {
        "methods": [],
        "datasets": [],
        "metrics": [],
        "cited_paper_ids": [],
    }


def test_graph_builder_constructs_typed_nodes_edges_and_shared_bridges():
    """Verify NetworkX DiGraph builds Paper, Author, Method, Dataset, Metric nodes and typed edges."""
    papers, chunks_by_paper = _sample_papers_and_chunks()
    builder = KnowledgeGraphBuilder()
    g = builder.build_graph(papers, chunks_by_paper)

    assert g.number_of_nodes() >= 10
    assert g.number_of_edges() >= 10

    # Verify cross-paper CITES edge (LoRA -> Vaswani)
    assert g.has_edge("node_paper_hu2021", "node_paper_vaswani2017")
    assert g.edges["node_paper_hu2021", "node_paper_vaswani2017"]["type"] == "CITES"

    # Verify shared Method node ("Self-Attention") is proposed/used by both papers
    assert g.has_edge("node_paper_vaswani2017", "node_method_self_attention")
    assert g.has_edge("node_paper_hu2021", "node_method_self_attention")

    # Verify node metadata includes rich scientific explanation and per-paper relation breakdown
    sa_meta = g.nodes["node_method_self_attention"]["metadata"]
    assert len(sa_meta["description"]) > 20
    assert len(sa_meta["paper_relations"]) == 2
    roles_by_paper = {r["paper_id"]: r["role"] for r in sa_meta["paper_relations"]}
    assert roles_by_paper["paper_vaswani2017"] == "Introduces / Proposes"
    assert roles_by_paper["paper_hu2021"] == "Builds On / Evaluates"
    assert all(len(r["explanation"]) > 15 and r["page"] >= 1 for r in sa_meta["paper_relations"])

    # Serialize idle Cytoscape topology
    cy_res = builder.to_cytoscape(min_degree=1)
    assert cy_res.total_nodes == len(cy_res.elements.nodes)
    assert cy_res.total_edges == len(cy_res.elements.edges)

    node_types = {n.data.type for n in cy_res.elements.nodes}
    assert {"Paper", "Author", "Method", "Dataset", "Metric"}.issubset(node_types)

    # Filter by entity_type='Method'
    method_only = builder.to_cytoscape(entity_type="Method", min_degree=1)
    assert all(n.data.type == "Method" for n in method_only.elements.nodes)


def test_graph_builder_prompt_activated_relevance_and_dimming():
    """Verify prompt-active mode scales relevant nodes (>=0.70), lights active edges, and dims peripheral nodes."""
    papers, chunks_by_paper = _sample_papers_and_chunks()
    builder = KnowledgeGraphBuilder()
    builder.build_graph(papers, chunks_by_paper)
    all_chunks = chunks_by_paper["paper_vaswani2017"] + chunks_by_paper["paper_hu2021"]

    highlighted = builder.to_cytoscape(
        query="LoRA low-rank decomposition on WikiSQL",
        active_chunk_ids=["paper_hu2021_c0"],
        all_chunks=all_chunks,
    )

    nodes_by_id = {n.data.id: n.data for n in highlighted.elements.nodes}
    assert nodes_by_id["node_paper_hu2021"].relevance_score >= 0.90
    assert nodes_by_id["node_paper_hu2021"].is_dimmed is False
    assert nodes_by_id["node_method_lora"].relevance_score >= 0.90
    assert nodes_by_id["node_method_lora"].is_dimmed is False

    # Unrelated nodes (e.g. Vaswani author node) should be dimmed
    assert nodes_by_id["node_author_ashish_vaswani"].is_dimmed is True

    # Edge between paper_hu2021 and method_lora should be active
    lora_edges = [
        e.data
        for e in highlighted.elements.edges
        if e.data.source == "node_paper_hu2021" and e.data.target == "node_method_lora"
    ]
    assert len(lora_edges) == 1
    assert lora_edges[0].is_active is True
    assert lora_edges[0].is_dimmed is False


def test_graph_api_endpoints_end_to_end():
    """Verify GET /api/graph and POST /api/graph/highlight conform to REST API contracts."""
    client = TestClient(app)

    # 1. Idle graph topology
    res = client.get("/api/graph?min_degree=1")
    assert res.status_code == 200
    body = res.json()
    assert body["total_nodes"] >= 15
    assert body["total_edges"] >= 20
    assert len(body["elements"]["nodes"]) == body["total_nodes"]

    # 2. Query-activated graph highlight
    hl_res = client.post(
        "/api/graph/highlight",
        json={
            "query": "FlashAttention IO-aware tiling GPU memory",
            "active_chunk_ids": ["paper_dao2022_c1"],
        },
    )
    assert hl_res.status_code == 200
    hl_body = hl_res.json()
    active_nodes = [
        n for n in hl_body["elements"]["nodes"] if (n["data"]["relevance_score"] or 0) >= 0.70
    ]
    dimmed_nodes = [n for n in hl_body["elements"]["nodes"] if n["data"]["is_dimmed"] is True]
    assert len(active_nodes) >= 2
    assert len(dimmed_nodes) >= 5

