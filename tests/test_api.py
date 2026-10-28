"""Comprehensive FastAPI endpoint integration and contract tests (T032):
Covers /api/health, /api/documents, /api/documents/{paper_id}/pdf, /api/query,
/api/graph, and /api/graph/highlight across general and edge cases.
"""

from pathlib import Path
from fastapi.testclient import TestClient

from backend.api.query_routes import extract_seed_chunks_from_pdf
from backend.models.paper import BoundingBox, PaperMetadata, TextChunk
from backend.rag.generator import REFUSAL_MESSAGE
from backend.scripts.seed_pdfs_builder import SEED_PAPERS_MANIFEST, build_pdf_bytes
from backend.storage.db import db
from backend.storage.file_store import FileStoreManager


def test_api_health_readiness_contract(api_client: TestClient):
    """Verify GET /api/health returns 200 OK with all required readiness booleans."""
    res = api_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    expected_keys = {
        "status",
        "version",
        "sqlite_connected",
        "chromadb_ready",
        "embedding_model_loaded",
        "cross_encoder_loaded",
        "spacy_loaded",
        "gemini_api_configured",
    }
    assert expected_keys.issubset(data.keys())
    assert data["status"] == "healthy"
    assert data["sqlite_connected"] is True
    assert data["chromadb_ready"] is True


def test_api_documents_list_and_pdf_binary_stream(api_client: TestClient):
    """Verify GET /api/documents lists all 5 seed papers and streams valid PDF binaries."""
    res = api_client.get("/api/documents")
    assert res.status_code == 200
    papers = res.json()
    assert len(papers) >= 5

    first_paper = papers[0]
    assert "id" in first_paper
    assert "title" in first_paper
    assert first_paper["total_pages"] >= 1

    # Stream PDF for paper_vaswani2017
    pdf_res = api_client.get("/api/documents/paper_vaswani2017/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")

    # Edge case: nonexistent paper_id returns 404
    missing_res = api_client.get("/api/documents/nonexistent_paper_id/pdf")
    assert missing_res.status_code == 404


def test_api_delete_temporary_document_lifecycle(api_client: TestClient):
    """Verify DELETE /api/documents/{paper_id} removes a temporary paper and returns 404 when repeated."""
    temp_paper = PaperMetadata(
        id="paper_temp_delete_test",
        title="Temporary Test Paper for Deletion",
        authors=["Test Author"],
        year=2025,
        filepath="data/papers/vaswani2017_attention.pdf",
        total_pages=1,
    )
    temp_chunk = TextChunk(
        id="paper_temp_delete_test_c0",
        paper_id="paper_temp_delete_test",
        paper_title=temp_paper.title,
        section="Abstract",
        page_number=1,
        bbox=BoundingBox(page=1, x=0.1, y=0.1, width=0.8, height=0.2),
        text="Temporary test chunk for deletion lifecycle verification.",
        token_count=8,
    )
    db.upsert_paper(temp_paper)
    db.save_chunks([temp_chunk])

    del_res = api_client.delete("/api/documents/paper_temp_delete_test")
    assert del_res.status_code == 200
    assert del_res.json() == {"deleted": True, "paper_id": "paper_temp_delete_test"}

    # Deleting again must return 404
    del_again = api_client.delete("/api/documents/paper_temp_delete_test")
    assert del_again.status_code == 404


def test_api_query_validation_and_paper_filter(api_client: TestClient):
    """Verify POST /api/query validates input constraints and respects paper_ids filter."""
    # Edge case: query shorter than 3 chars rejected with 422 Unprocessable Entity
    short_res = api_client.post("/api/query", json={"query": "hi"})
    assert short_res.status_code == 422

    # Edge case: top_k out of range [1, 20] rejected with 422
    bad_topk = api_client.post("/api/query", json={"query": "Valid query string", "top_k": 99})
    assert bad_topk.status_code == 422

    # Valid filtered query restricted to paper_dao2022 (FlashAttention)
    filtered_res = api_client.post(
        "/api/query",
        json={
            "query": "How does FlashAttention use IO-aware tiling in SRAM to reduce HBM memory accesses?",
            "top_k": 3,
            "paper_ids": ["paper_dao2022"],
        },
    )
    assert filtered_res.status_code == 200
    body = filtered_res.json()
    assert body["status"] == "success"
    assert len(body["citations"]) >= 1
    assert all(c["paper_id"] == "paper_dao2022" for c in body["citations"])


def test_api_query_out_of_scope_zero_hallucination(api_client: TestClient):
    """Verify POST /api/query triggers deterministic refusal on out-of-scope questions."""
    res = api_client.post(
        "/api/query",
        json={
            "query": "What is the volcanic eruption frequency of Mount Vesuvius in the Bronze Age?",
            "top_k": 5,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "insufficient_context"
    assert body["answer"] == REFUSAL_MESSAGE
    assert body["citations"] == []


def test_api_graph_topology_and_highlight_contracts(api_client: TestClient):
    """Verify GET /api/graph filtering and POST /api/graph/highlight node explanations & active paths."""
    # 1. Full graph
    g_res = api_client.get("/api/graph?min_degree=1")
    assert g_res.status_code == 200
    g_data = g_res.json()
    assert g_data["total_nodes"] >= 15
    assert g_data["total_edges"] >= 15

    # Verify Method nodes carry description and paper_relations metadata
    method_nodes = [
        n["data"] for n in g_data["elements"]["nodes"] if n["data"]["type"] == "Method"
    ]
    assert len(method_nodes) >= 3
    for mnode in method_nodes:
        assert "description" in mnode["metadata"]
        assert "paper_relations" in mnode["metadata"]
        assert len(mnode["metadata"]["paper_relations"]) >= 1

    # 2. Filtered graph by entity_type=Paper
    p_res = api_client.get("/api/graph?entity_type=Paper&min_degree=1")
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert all(n["data"]["type"] == "Paper" for n in p_data["elements"]["nodes"])

    # 3. Highlight endpoint with query and active_chunk_ids
    hl_res = api_client.post(
        "/api/graph/highlight",
        json={
            "query": "Rotary Position Embedding RoPE in RoFormer",
            "active_chunk_ids": ["paper_su2021_c0"],
        },
    )
    assert hl_res.status_code == 200
    hl_data = hl_res.json()
    roformer_node = next(
        n["data"]
        for n in hl_data["elements"]["nodes"]
        if n["data"]["id"] == "node_paper_su2021"
    )
    assert roformer_node["relevance_score"] >= 0.90
    assert roformer_node["is_dimmed"] is False



def test_seed_pdf_builder_and_chunk_extractor_unit(tmp_path: Path):
    """Verify build_pdf_bytes, FileStoreManager.copy_pdf_file, and extract_seed_chunks_from_pdf."""
    spec = SEED_PAPERS_MANIFEST[0]
    raw_pdf = build_pdf_bytes(spec)
    assert raw_pdf.startswith(b"%PDF-1.4")

    src_pdf = tmp_path / "source_sample.pdf"
    src_pdf.write_bytes(raw_pdf)

    store = FileStoreManager(base_dir=tmp_path / "store")
    copied = store.copy_pdf_file(src_pdf, target_filename="copied_vaswani")
    assert copied.name == "copied_vaswani.pdf"
    rel = store.get_relative_filepath(copied)
    assert isinstance(rel, str) and len(rel) > 0

    chunks, num_pages = extract_seed_chunks_from_pdf(spec, copied)
    assert num_pages == 3
    assert len(chunks) >= 3
    assert all(0.0 <= c.bbox.x <= 1.0 and 0.0 < c.bbox.width <= 1.0 for c in chunks)
