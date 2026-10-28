"""Automated unit and contract tests for Hybrid RAG retrieval (T012):
BM25 indexing, ChromaDB vector retrieval, RRF (k=60) fusion, and Cross-Encoder re-ranking.
"""

from pathlib import Path
from typing import List
import pytest

from backend.models.paper import BoundingBox, TextChunk
from backend.rag.bm25_index import BM25IndexManager, tokenize_scientific_text
from backend.rag.reranker import HybridReranker, reciprocal_rank_fusion
from backend.rag.vector_store import VectorStoreManager


def _sample_chunks() -> List[TextChunk]:
    return [
        TextChunk(
            id="paper_vaswani2017_c1",
            paper_id="paper_vaswani2017",
            paper_title="Attention Is All You Need",
            section="Scaled Dot-Product Attention",
            page_number=2,
            bbox=BoundingBox(page=2, x=0.08, y=0.22, width=0.82, height=0.14),
            text="We compute the dot products of the query with all keys, divide each by 1/sqrt(d_k) scaling factor, and apply a softmax function.",
            token_count=22,
        ),
        TextChunk(
            id="paper_hu2021_c1",
            paper_id="paper_hu2021",
            paper_title="LoRA: Low-Rank Adaptation of Large Language Models",
            section="Abstract",
            page_number=1,
            bbox=BoundingBox(page=1, x=0.08, y=0.35, width=0.84, height=0.18),
            text="LoRA freezes the pre-trained model weights and injects trainable rank decomposition matrices, reducing trainable parameters by 10,000 times and GPU memory by 3-fold.",
            token_count=24,
        ),
        TextChunk(
            id="paper_dao2022_c1",
            paper_id="paper_dao2022",
            paper_title="FlashAttention: Fast and Memory-Efficient Exact Attention",
            section="Algorithm",
            page_number=2,
            bbox=BoundingBox(page=2, x=0.09, y=0.25, width=0.80, height=0.16),
            text="FlashAttention uses IO-aware tiling between GPU HBM and on-chip SRAM to reduce memory complexity from O(N^2) to linear O(N).",
            token_count=21,
        ),
    ]


def test_scientific_tokenization_preserves_technical_terms():
    """Verify scientific tokenizer keeps hyphenated terms, underscores, and normalizes numbers."""
    tokens = tokenize_scientific_text("GPT-3 175B uses d_k scaling and reduces parameters by 10,000 times.")
    assert "gpt-3" in tokens
    assert "175b" in tokens
    assert "d_k" in tokens
    assert "10000" in tokens
    # Stopwords removed
    assert "and" not in tokens
    assert "by" not in tokens
    assert tokenize_scientific_text("") == []


def test_bm25_index_search_and_paper_filtering():
    """Verify BM25 lexical search ranks exact technical terminology highest and supports paper_ids filter."""
    idx = BM25IndexManager()
    chunks = _sample_chunks()
    assert idx.build_index(chunks) == 3

    hits = idx.search("1/sqrt(d_k) scaling factor dot products", top_k=5)
    assert len(hits) >= 1
    assert hits[0]["chunk"].id == "paper_vaswani2017_c1"
    assert hits[0]["rank"] == 1
    assert hits[0]["score"] > 0.0

    # Filter to only paper_hu2021
    filtered = idx.search("attention matrices", top_k=5, paper_ids=["paper_hu2021"])
    for item in filtered:
        assert item["chunk"].paper_id == "paper_hu2021"

    # Edge cases: empty query or unindexed manager
    assert idx.search("   ") == []
    empty_idx = BM25IndexManager()
    assert empty_idx.build_index([]) == 0
    assert empty_idx.search("LoRA") == []


def test_reciprocal_rank_fusion_math_and_deduplication():
    """Verify RRF(k=60) accurately sums 1/(60 + rank) across sparse and dense lists and deduplicates."""
    chunks = _sample_chunks()
    c_vaswani, c_lora, c_flash = chunks[0], chunks[1], chunks[2]

    # c_lora is Rank 1 in BM25 and Rank 2 in Vector -> RRF = 1/61 + 1/62
    # c_vaswani is Rank 2 in BM25 only -> RRF = 1/62
    # c_flash is Rank 1 in Vector only -> RRF = 1/61
    bm25_res = [
        {"chunk": c_lora, "score": 8.5, "rank": 1},
        {"chunk": c_vaswani, "score": 4.2, "rank": 2},
    ]
    vec_res = [
        {"chunk": c_flash, "score": 0.91, "rank": 1},
        {"chunk": c_lora, "score": 0.88, "rank": 2},
    ]

    fused = reciprocal_rank_fusion(bm25_res, vec_res, k=60)
    assert len(fused) == 3
    assert fused[0]["chunk"].id == "paper_hu2021_c1"

    expected_lora_rrf = (1.0 / 61.0) + (1.0 / 62.0)
    assert pytest.approx(fused[0]["rrf_score"], rel=1e-6) == expected_lora_rrf
    assert fused[0]["bm25_rank"] == 1
    assert fused[0]["vector_rank"] == 2

    # Edge case: invalid k < 1 raises ValueError
    with pytest.raises(ValueError, match="RRF constant k must be >= 1"):
        reciprocal_rank_fusion(bm25_res, vec_res, k=0)


def test_hybrid_reranker_orders_by_cross_encoder_relevance(tmp_path: Path):
    """Verify full BM25 + ChromaDB -> RRF -> Cross-Encoder pipeline returns top passages with valid scores."""
    chunks = _sample_chunks()
    bm25 = BM25IndexManager()
    bm25.build_index(chunks)

    # Deterministic 384-d embedder for fast unit test
    def mock_embed(texts: List[str]) -> List[List[float]]:
        out = []
        for t in texts:
            tl = t.lower()
            v = [0.0] * 384
            if "lora" in tl or "10,000" in tl or "parameter" in tl:
                v[0] = 1.0
            elif "sqrt" in tl or "vaswani" in tl:
                v[1] = 1.0
            else:
                v[2] = 1.0
            out.append(v)
        return out

    vs = VectorStoreManager(
        persist_dir=tmp_path / "chroma_rag",
        collection_name="rag_test",
        embedding_fn=mock_embed,
    )
    vs.index_chunks(chunks)

    query = "How much does LoRA reduce trainable parameters and GPU memory?"
    bm25_hits = bm25.search(query, top_k=5)
    vec_hits = vs.search(query, top_k=5)

    # Mock Cross-Encoder scorer assigning highest probability to passage mentioning LoRA
    def mock_ce_scorer(q: str, passages: List[str]) -> List[float]:
        return [0.96 if "LoRA" in p else 0.18 for p in passages]

    custom_reranker = HybridReranker(rrf_k=60, scorer_fn=mock_ce_scorer)
    ranked = custom_reranker.fuse_and_rerank(query, bm25_hits, vec_hits, top_n=2)

    assert len(ranked) == 2
    assert ranked[0]["chunk"].id == "paper_hu2021_c1"
    assert 0.0 <= ranked[0]["relevance_score"] <= 1.0
    assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]
    assert ranked[0]["final_rank"] == 1

