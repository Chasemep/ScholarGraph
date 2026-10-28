"""Automated integration tests for grounded citation verification and 0.0% hallucination fallback (T013)."""

from fastapi.testclient import TestClient

from backend.main import app
from backend.models.paper import BoundingBox, TextChunk
from backend.rag.generator import (
    REFUSAL_MESSAGE,
    GroundedGenerator,
    extractive_fallback_synthesis,
)


def _sample_ranked_candidates():
    c1 = TextChunk(
        id="paper_hu2021_c0",
        paper_id="paper_hu2021",
        paper_title="LoRA: Low-Rank Adaptation of Large Language Models",
        section="Abstract",
        page_number=1,
        bbox=BoundingBox(page=1, x=0.08, y=0.35, width=0.84, height=0.18),
        text="Compared to GPT-3 175B fine-tuned with Adam, LoRA can reduce the number of trainable parameters by 10,000 times and the GPU memory requirement by 3-fold.",
        token_count=26,
    )
    c2 = TextChunk(
        id="paper_vaswani2017_c1",
        paper_id="paper_vaswani2017",
        paper_title="Attention Is All You Need",
        section="Scaled Dot-Product Attention",
        page_number=2,
        bbox=BoundingBox(page=2, x=0.08, y=0.22, width=0.82, height=0.14),
        text="We compute the dot products of the query with all keys, divide each by the square root of d_k (1 / sqrt(d_k) scaling factor), and apply a softmax function.",
        token_count=28,
    )
    return [
        {
            "chunk": c1,
            "relevance_score": 0.92,
            "rrf_score": 0.032,
            "bm25_rank": 1,
            "vector_rank": 1,
        },
        {
            "chunk": c2,
            "relevance_score": 0.85,
            "rrf_score": 0.030,
            "bm25_rank": 2,
            "vector_rank": 2,
        },
    ]


def test_extractive_fallback_produces_grounded_inline_citations():
    """Verify deterministic extractive synthesis embeds [paper_id, Page X] tokens for every claim."""
    candidates = _sample_ranked_candidates()
    answer = extractive_fallback_synthesis(
        "Compare LoRA trainable parameters and scaled dot-product attention",
        candidates,
    )
    assert "[paper_hu2021, Page 1]" in answer
    assert "[paper_vaswani2017, Page 2]" in answer


def test_generator_with_mock_gemini_llm_and_citation_validation():
    """Verify GroundedGenerator uses Gemini response when valid citations are present."""
    candidates = _sample_ranked_candidates()

    def mock_gemini(_sys: str, _prompt: str, _key: str) -> str:
        return (
            "LoRA reduces trainable parameters by 10,000 times and GPU memory by 3-fold "
            "[paper_hu2021, Page 1], whereas Vaswani et al. scale dot products by 1/sqrt(d_k) "
            "[paper_vaswani2017, Page 2]."
        )

    gen = GroundedGenerator(llm_callable=mock_gemini)
    out = gen.generate(
        query="Compare LoRA parameter efficiency and scaled dot-product attention.",
        ranked_candidates=candidates,
        api_key_override="mock-gemini-key",
    )
    assert out["status"] == "success"
    assert "[paper_hu2021, Page 1]" in out["answer"]
    assert len(out["citations"]) == 2
    assert out["citations"][0].bbox.to_list() == [1, 0.08, 0.35, 0.84, 0.18]


def test_generator_zero_hallucination_refusal_on_out_of_scope_query():
    """Edge Case (Zero-Hallucination Invariant): Out-of-scope query must return exact refusal and 0 citations."""
    candidates = _sample_ranked_candidates()
    # Lower relevance scores to simulate non-matching domain query
    low_candidates = [
        {**c, "relevance_score": 0.12, "bm25_rank": None}
        for c in candidates
    ]

    gen = GroundedGenerator()
    out = gen.generate(
        query="What is the optimal soil pH for growing Macintosh apples in Vermont?",
        ranked_candidates=low_candidates,
    )
    assert out["status"] == "insufficient_context"
    assert out["answer"] == REFUSAL_MESSAGE
    assert out["citations"] == []
    assert out["model_used"] == "deterministic-guardrail"


def test_api_query_and_pdf_streaming_endpoints_end_to_end():
    """Integration test for POST /api/query, GET /api/documents, and GET /api/documents/{paper_id}/pdf."""
    client = TestClient(app)

    # 1. List indexed seed documents
    docs_res = client.get("/api/documents")
    assert docs_res.status_code == 200
    docs = docs_res.json()
    assert len(docs) >= 5
    paper_ids = {d["id"] for d in docs}
    assert "paper_vaswani2017" in paper_ids
    assert "paper_hu2021" in paper_ids

    # 2. Stream PDF binary for paper_hu2021
    pdf_res = client.get("/api/documents/paper_hu2021/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content[:5] == b"%PDF-"

    # Edge case: 404 on unknown paper_id
    not_found_res = client.get("/api/documents/paper_nonexistent_999/pdf")
    assert not_found_res.status_code == 404

    # 3. Comparative in-scope query via POST /api/query
    query_res = client.post(
        "/api/query",
        json={
            "query": "How does LoRA reduce trainable parameters and GPU memory compared to full fine-tuning?",
            "top_k": 5,
        },
    )
    assert query_res.status_code == 200
    payload = query_res.json()
    assert payload["status"] == "success"
    assert len(payload["citations"]) >= 1
    top_cit = payload["citations"][0]
    assert top_cit["paper_id"] == "paper_hu2021"
    assert top_cit["page"] >= 1
    assert 0.0 <= top_cit["bbox"]["x"] <= 1.0
    assert 0.0 < top_cit["bbox"]["width"] <= 1.0

    # 4. Out-of-scope query triggers insufficient_context refusal
    oos_res = client.post(
        "/api/query",
        json={
            "query": "What is the synthesis temperature of superconducting cuprate perovskites?",
            "top_k": 5,
        },
    )
    assert oos_res.status_code == 200
    oos_payload = oos_res.json()
    assert oos_payload["status"] == "insufficient_context"
    assert oos_payload["answer"] == REFUSAL_MESSAGE
    assert oos_payload["citations"] == []

