"""Candidate fusion via Reciprocal Rank Fusion (RRF, k=60) and Cross-Encoder re-ranking."""

import math
from typing import Any, Callable, Dict, List, Optional

from backend.config import settings
from backend.models.paper import TextChunk

CROSS_ENCODER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_shared_cross_encoder: Any = None


def get_cross_encoder():
    """Lazy-load and cache the singleton CrossEncoder model."""
    global _shared_cross_encoder
    if _shared_cross_encoder is None:
        from sentence_transformers import CrossEncoder

        _shared_cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL_NAME)
    return _shared_cross_encoder


def _sigmoid(x: float) -> float:
    """Map raw cross-encoder logits into a calibrated [0.0, 1.0] probability."""
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def default_cross_encoder_scorer(query: str, passages: List[str]) -> List[float]:
    """Score (query, passage) pairs with ms-marco-MiniLM-L-6-v2 and normalize via sigmoid."""
    if not passages:
        return []
    model = get_cross_encoder()
    pairs = [(query, p) for p in passages]
    raw_scores = model.predict(pairs, show_progress_bar=False)
    return [_sigmoid(float(s)) for s in raw_scores]


def reciprocal_rank_fusion(
    bm25_results: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Fuse sparse BM25 and dense vector rankings using Reciprocal Rank Fusion:

    RRF_score(d) = sum_{r in R} 1 / (k + rank_r(d))
    """
    if k < 1:
        raise ValueError("RRF constant k must be >= 1")

    fused: Dict[str, Dict[str, Any]] = {}

    for rank_idx, item in enumerate(bm25_results, start=1):
        chunk: TextChunk = item["chunk"]
        rank = int(item.get("rank", rank_idx))
        rrf_contrib = 1.0 / (k + rank)
        entry = fused.setdefault(
            chunk.id,
            {
                "chunk": chunk,
                "rrf_score": 0.0,
                "bm25_rank": None,
                "vector_rank": None,
                "bm25_score": 0.0,
                "vector_score": 0.0,
            },
        )
        entry["rrf_score"] += rrf_contrib
        entry["bm25_rank"] = rank
        entry["bm25_score"] = float(item.get("score", 0.0))

    for rank_idx, item in enumerate(vector_results, start=1):
        chunk = item["chunk"]
        rank = int(item.get("rank", rank_idx))
        rrf_contrib = 1.0 / (k + rank)
        entry = fused.setdefault(
            chunk.id,
            {
                "chunk": chunk,
                "rrf_score": 0.0,
                "bm25_rank": None,
                "vector_rank": None,
                "bm25_score": 0.0,
                "vector_score": 0.0,
            },
        )
        entry["rrf_score"] += rrf_contrib
        entry["vector_rank"] = rank
        entry["vector_score"] = float(item.get("score", 0.0))

    sorted_candidates = sorted(
        fused.values(),
        key=lambda x: (x["rrf_score"], x["vector_score"], x["bm25_score"]),
        reverse=True,
    )
    for idx, cand in enumerate(sorted_candidates, start=1):
        cand["fused_rank"] = idx
    return sorted_candidates


class HybridReranker:
    """Combines RRF candidate fusion with neural Cross-Encoder re-ranking."""

    def __init__(
        self,
        rrf_k: int = settings.rrf_k,
        scorer_fn: Optional[Callable[[str, List[str]], List[float]]] = None,
    ) -> None:
        self.rrf_k = rrf_k
        self._scorer_fn = scorer_fn or default_cross_encoder_scorer

    def fuse_and_rerank(
        self,
        query: str,
        bm25_results: List[Dict[str, Any]],
        vector_results: List[Dict[str, Any]],
        top_n: int = settings.rerank_top_n,
    ) -> List[Dict[str, Any]]:
        """Fuse sparse + dense candidates via RRF and re-rank using the Cross-Encoder."""
        if not query or not query.strip():
            return []

        fused_candidates = reciprocal_rank_fusion(bm25_results, vector_results, k=self.rrf_k)
        if not fused_candidates:
            return []

        passages = [
            f"{c['chunk'].paper_title or c['chunk'].paper_id} ({c['chunk'].section}): {c['chunk'].text}"
            for c in fused_candidates
        ]
        ce_scores = self._scorer_fn(query, passages)

        for cand, ce_score in zip(fused_candidates, ce_scores):
            # Combine calibrated cross-encoder probability with lexical/semantic signals
            # Also zero out unrelated candidates when BM25 found 0 lexical hits and cross-encoder score is low
            has_lexical_hit = cand["bm25_rank"] is not None
            norm_ce = max(0.0, min(1.0, float(ce_score)))
            if has_lexical_hit:
                # Boost slightly when both lexical and neural cross-attention agree
                combined = min(1.0, 0.80 * norm_ce + 0.20 * min(1.0, cand["vector_score"]))
            else:
                combined = 0.70 * norm_ce + 0.30 * max(0.0, cand["vector_score"] - 0.15)
            cand["relevance_score"] = round(max(0.0, min(1.0, combined)), 4)

        reranked = sorted(
            fused_candidates,
            key=lambda x: (x["relevance_score"], x["rrf_score"]),
            reverse=True,
        )
        top_passages = reranked[:top_n]
        for idx, item in enumerate(top_passages, start=1):
            item["final_rank"] = idx
        return top_passages


reranker = HybridReranker()

