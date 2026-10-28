"""Candidate fusion via Reciprocal Rank Fusion (RRF, k=60) and Cross-Encoder re-ranking."""

import math
import re
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


def _clean_query_for_cross_encoder(query: str) -> str:
    """Strip meta-instruction boilerplate so the MS-MARCO Cross-Encoder focuses on scientific concepts."""
    cleaned = re.sub(
        r"\b(?:explain|compare\s+how\s+each\s+paper\s+in\s+the\s+corpus|in\s+the\s+corpus|"
        r"proposes,?\s*adapts,?\s*or\s*evaluates\s+it|compare\s+and\s+contrast)\b",
        " ",
        query,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;:")
    return cleaned if len(cleaned) >= 3 else query


def default_cross_encoder_scorer(query: str, passages: List[str]) -> List[float]:
    """Score (query, passage) pairs with ms-marco-MiniLM-L-6-v2 and normalize via sigmoid."""
    if not passages:
        return []
    model = get_cross_encoder()
    focused_query = _clean_query_for_cross_encoder(query)
    pairs = [(focused_query, p) for p in passages]
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

        # Limit Cross-Encoder pool to top 16 RRF candidates to keep latency < 800ms
        # while ensuring at least the top candidate from each paper in the RRF pool is included
        pool_limit = max(16, top_n * 2)
        seen_papers: set[str] = set()
        diverse_pool: List[Dict[str, Any]] = []
        remainder_pool: List[Dict[str, Any]] = []

        for cand in fused_candidates:
            pid = cand["chunk"].paper_id
            if pid not in seen_papers:
                seen_papers.add(pid)
                diverse_pool.append(cand)
            else:
                remainder_pool.append(cand)

        candidates_for_ce = (diverse_pool + remainder_pool)[:pool_limit]

        passages = [
            f"{c['chunk'].paper_title or c['chunk'].paper_id} ({c['chunk'].section}): {c['chunk'].text}"
            for c in candidates_for_ce
        ]
        ce_scores = self._scorer_fn(query, passages)

        max_bm25 = max((c["bm25_score"] for c in candidates_for_ce), default=0.0)

        for cand, ce_score in zip(candidates_for_ce, ce_scores):
            has_lexical_hit = cand["bm25_rank"] is not None
            norm_ce = max(0.0, min(1.0, float(ce_score)))
            norm_bm25 = (cand["bm25_score"] / max_bm25) if max_bm25 > 0 else 0.0
            vec_sim = max(0.0, min(1.0, float(cand["vector_score"])))

            if has_lexical_hit:
                # Hybrid calibration combining Cross-Encoder, normalized BM25, and dense cosine similarity
                combined = 0.55 * norm_ce + 0.25 * norm_bm25 + 0.20 * vec_sim
                # Floor when both BM25 and dense vector agree strongly on a broad domain term
                if norm_bm25 >= 0.40 and vec_sim >= 0.30:
                    combined = max(combined, 0.45 + 0.35 * norm_bm25)
            else:
                combined = 0.70 * norm_ce + 0.30 * max(0.0, vec_sim - 0.20)

            cand["relevance_score"] = round(max(0.0, min(1.0, combined)), 4)

        reranked = sorted(
            candidates_for_ce,
            key=lambda x: (x["relevance_score"], x["rrf_score"]),
            reverse=True,
        )

        # If the user asks a multi-paper comparative question, ensure paper diversity in top_n
        ql = query.lower()
        is_multi_paper_query = any(
            kw in ql for kw in ["each paper", "compare", "corpus", "papers", "across"]
        )
        if is_multi_paper_query and len(reranked) > top_n:
            selected: List[Dict[str, Any]] = []
            selected_ids: set[str] = set()
            covered_papers: set[str] = set()

            # First pick the top-scoring passage from each paper that meets relevance threshold
            for cand in reranked:
                pid = cand["chunk"].paper_id
                if (
                    pid not in covered_papers
                    and cand["relevance_score"] >= settings.min_relevance_threshold
                    and len(selected) < top_n
                ):
                    covered_papers.add(pid)
                    selected.append(cand)
                    selected_ids.add(cand["chunk"].id)

            # Fill remaining slots up to top_n by highest relevance_score
            for cand in reranked:
                if len(selected) >= top_n:
                    break
                if cand["chunk"].id not in selected_ids:
                    selected.append(cand)
                    selected_ids.add(cand["chunk"].id)

            top_passages = sorted(
                selected,
                key=lambda x: (x["relevance_score"], x["rrf_score"]),
                reverse=True,
            )
        else:
            top_passages = reranked[:top_n]

        for idx, item in enumerate(top_passages, start=1):
            item["final_rank"] = idx
        return top_passages


reranker = HybridReranker()
