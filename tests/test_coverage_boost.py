"""Targeted Unit and Integration tests to maximize coverage beyond 85% across RAG, APIs, and Parsers."""

import pytest
from unittest.mock import MagicMock, patch
from backend.models.paper import TextChunk, BoundingBox
from backend.rag.generator import (
    GroundedGenerator,
    generator,
    generate_clarifying_refusal,
    _repair_bare_page_citations,
    extractive_fallback_synthesis,
    _has_query_overlap,
    REFUSAL_MESSAGE,
)
from backend.api.query_routes import (
    _math_density,
    _model_definition_score,
    _is_comparative_query,
    _is_formula_query,
    _is_followup_query,
    _is_boilerplate_chunk,
)
from backend.main import app
from fastapi.testclient import TestClient


def _make_dummy_chunk(chunk_id: str, paper_id: str, text: str, page: int = 1, section: str = "Methods") -> TextChunk:
    return TextChunk(
        id=chunk_id,
        paper_id=paper_id,
        page_number=page,
        text=text,
        section=section,
        bbox=BoundingBox(page=page, x=0.1, y=0.1, width=0.8, height=0.2),
        paper_title=f"Title of {paper_id}",
        token_count=len(text.split()),
    )


def test_repair_bare_page_citations():
    # Single paper preceding citation
    text = "Under [paper_vaswani2017, Page 1], the attention mechanism is computed as follows [Page 3] and also [p. 4]."
    repaired = _repair_bare_page_citations(text, {"paper_vaswani2017"})
    assert "[paper_vaswani2017, Page 3]" in repaired
    assert "[paper_vaswani2017, Page 4]" in repaired

    # Markdown table columns
    table_text = "| paper_hu2021 | paper_vaswani2017 |\n| [Page 2] | [Page 5] |"
    repaired_table = _repair_bare_page_citations(table_text, {"paper_hu2021", "paper_vaswani2017"})
    assert "[paper_hu2021, Page 2]" in repaired_table
    assert "[paper_vaswani2017, Page 5]" in repaired_table


def test_has_query_overlap():
    chunk = _make_dummy_chunk("c1", "p1", "Self-attention layer computes scaled dot product representations.")
    cand = {"chunk": chunk, "relevance_score": 0.8}

    # Meaningful overlap
    assert _has_query_overlap("How does self-attention work?", [cand]) is True

    # Empty candidate list
    assert _has_query_overlap("How does self-attention work?", []) is False

    # Empty query
    assert _has_query_overlap("", [cand]) is False

    # Irrelevant query
    irrel_chunk = _make_dummy_chunk("c2", "p2", "Ancient Mesopotamian irrigation canals and barley agriculture.")
    irrel_cand = {"chunk": irrel_chunk, "relevance_score": 0.1}
    assert _has_query_overlap("quantum cryptography key distribution", [irrel_cand]) is False


def test_generate_clarifying_refusal():
    # Without history
    res = generate_clarifying_refusal("What is the difference between the models?")
    assert res["status"] == "insufficient_context"
    assert len(res["suggested_followups"]) >= 1
    assert "Which model(s) are you referring to?" in res["suggested_followups"][0]

    # With dummy turn history referencing an indexed paper
    dummy_turn = MagicMock()
    dummy_turn.role = "assistant"
    dummy_turn.content = "Here is info about [paper_vaswani2017, Page 1]."
    dummy_turn.paper_ids = ["paper_vaswani2017"]
    res_hist = generate_clarifying_refusal("tell me more", history=[dummy_turn])
    assert res_hist["status"] == "insufficient_context"
    assert len(res_hist["suggested_followups"]) >= 1
    assert any("following up" in s.lower() or "vaswani" in s.lower() or "attention" in s.lower() for s in res_hist["suggested_followups"])


def test_extractive_fallback_synthesis():
    c1 = _make_dummy_chunk("c1", "paper_a", "Low rank adaptation modifies pre trained weights efficiently. It uses low rank matrix decomposition to optimize memory.", page=2)
    c2 = _make_dummy_chunk("c2", "paper_b", "Transformers employ multi-head attention. Each attention head operates in parallel.", page=5)
    candidates = [
        {"chunk": c1, "relevance_score": 0.9},
        {"chunk": c2, "relevance_score": 0.7},
    ]
    synthesis = extractive_fallback_synthesis("low rank adaptation memory", candidates)
    assert "[paper_a, Page 2]" in synthesis
    assert "Low rank adaptation" in synthesis


def test_quick_completion_and_gemini_fallback():
    gen = GroundedGenerator()

    # Quick completion success
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "rewritten query"}]}}]
    }
    with patch("httpx.Client.post", return_value=mock_resp):
        out = gen.quick_completion("test prompt", "fake_key")
        assert out == "rewritten query"

    # Quick completion failure handles gracefully
    with patch("httpx.Client.post", side_effect=Exception("network timeout")):
        out_err = gen.quick_completion("test prompt", "fake_key")
        assert out_err == ""


def test_generator_local_fallback_mode():
    gen = GroundedGenerator()
    c1 = _make_dummy_chunk("c1", "p1", "Adam optimizer computes adaptive learning rates for each parameter using first and second moments.")
    cand = {"chunk": c1, "relevance_score": 0.85}

    out = gen.generate(
        query="Adam learning rate moments",
        ranked_candidates=[cand],
        api_key_override="LOCAL_FALLBACK",
    )
    assert out["status"] == "success"
    assert out["model_used"] == "extractive-fallback"
    assert len(out["citations"]) >= 1
    assert "Adam optimizer" in out["answer"]


def test_query_route_helper_functions():
    # Math density
    math_text = "dv_i / dt = alpha / N * sum_{j=1}^N a_ij (v_j - v_i)"
    plain_text = "This is a simple textual description of neural network training without formulas."
    assert _math_density(math_text) > _math_density(plain_text)

    # Model definition score
    assert _model_definition_score(_make_dummy_chunk("c1", "p1", "The model is governed by the system of ordinary differential equations.", page=1)) > 1.5
    assert _model_definition_score(_make_dummy_chunk("c2", "p2", "We would like to thank our colleagues for discussions.", page=10)) < 0.2

    # Query intent classification
    assert _is_comparative_query("What are the differences between the 3 models?") is True
    assert _is_comparative_query("Compare ViT and ResNet architectures") is True
    assert _is_comparative_query("How does LoRA reduce memory compared to full fine-tuning?") is False

    assert _is_formula_query("What is the governing equation for velocity update?") is True
    assert _is_formula_query("Summarize the authors and contributions") is False

    # Followup query detection
    history = [MagicMock()]
    assert _is_followup_query("just the equations", history) is True
    assert _is_followup_query("what about the second one", history) is True
    assert _is_followup_query("what about the second one", []) is False

    # Boilerplate detection
    boilerplate_chunk = _make_dummy_chunk("c3", "p3", "Journal homepage: www.elsevier.com/locate/jmaa Copyright 2020 Elsevier B.V. All rights reserved.")
    assert _is_boilerplate_chunk(boilerplate_chunk) is True
    content_chunk = _make_dummy_chunk(
        "c4",
        "p4",
        "We introduce the residual learning framework to ease the training of networks that are substantially deeper than those used previously. Our explicit formulation facilitates deep representations without degradation.",
    )
    assert _is_boilerplate_chunk(content_chunk) is False


def test_api_delete_document_endpoints():
    client = TestClient(app)

    # 404 on nonexistent paper
    res_404 = client.delete("/api/documents/paper_nonexistent_test_999")
    assert res_404.status_code == 404

    # Delete existing test paper if present
    # We test deleting a temporary mock paper
    from backend.storage.db import db
    from backend.models.paper import PaperMetadata
    mock_paper = PaperMetadata(
        id="paper_temp_test_del",
        title="Temporary Paper for Deletion Test",
        authors=["Test Author"],
        year=2024,
        abstract="Test abstract",
        categories=["Computer Science"],
        subcategories=["AI"],
        doi=None,
        filepath="temp.pdf",
        total_pages=1,
        chunk_ids=["temp_c1"],
    )
    db.upsert_paper(mock_paper)
    del_res = client.delete("/api/documents/paper_temp_test_del")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True
    assert del_res.json()["paper_id"] == "paper_temp_test_del"
