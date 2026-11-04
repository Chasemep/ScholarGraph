"""Standardized 25-question Information Retrieval benchmark harness verifying MRR@5 >= 0.85 (T047).

Evaluates Sparse BM25, Dense ChromaDB Vector, Hybrid RRF, and Full Hybrid + Cross-Encoder re-ranking
across the 5-paper seed corpus, and formats Markdown tables for Chapter 5 of the technical report.
"""

import time
from typing import Any, Dict, List

from backend.api.query_routes import ensure_corpus_indexed
from backend.rag.bm25_index import bm25_index
from backend.rag.reranker import get_cross_encoder, reciprocal_rank_fusion, reranker
from backend.rag.vector_store import get_bi_encoder, vector_store

# Standardized 25-question IR benchmark dataset across the 5 seed papers
BENCHMARK_QUESTIONS: List[Dict[str, Any]] = [
    # paper_vaswani2017 (Attention Is All You Need)
    {
        "id": "Q01",
        "query": "What is the formula for Scaled Dot-Product Attention and why is 1/sqrt(d_k) used?",
        "expected_paper_id": "paper_vaswani2017",
        "expected_keywords": ["softmax", "dot", "products", " attention"],
    },
    {
        "id": "Q02",
        "query": "How does the Transformer architecture dispense with recurrence and convolutions using self-attention?",
        "expected_paper_id": "paper_vaswani2017",
        "expected_keywords": ["recurrence", "attention", "transformer"],
    },
    {
        "id": "Q03",
        "query": "What BLEU score did the big Transformer model achieve on the WMT 2014 English-to-German translation task?",
        "expected_paper_id": "paper_vaswani2017",
        "expected_keywords": ["28.4", "bleu", "wmt", "english-to-german"],
    },
    {
        "id": "Q04",
        "query": "How does Multi-Head Attention project queries, keys, and values into different representation subspaces?",
        "expected_paper_id": "paper_vaswani2017",
        "expected_keywords": ["multi-head", "queries", "keys", "values"],
    },
    {
        "id": "Q05",
        "query": "How are sinusoidal positional encodings with sine and cosine functions of different frequencies defined in Transformer?",
        "expected_paper_id": "paper_vaswani2017",
        "expected_keywords": ["positional", "sine", "cosine", "frequencies"],
    },
    # paper_devlin2019 (BERT)
    {
        "id": "Q06",
        "query": "How does BERT pre-train deep bidirectional representations using Masked Language Modeling (MLM)?",
        "expected_paper_id": "paper_devlin2019",
        "expected_keywords": ["bidirectional", "masked", "bert"],
    },
    {
        "id": "Q07",
        "query": "What percentage of tokens are masked in BERT's Cloze task and how are [MASK] tokens replaced?",
        "expected_paper_id": "paper_devlin2019",
        "expected_keywords": ["15%", "mask", "tokens"],
    },
    {
        "id": "Q08",
        "query": "How does the Next Sentence Prediction (NSP) objective work in BERT pre-training?",
        "expected_paper_id": "paper_devlin2019",
        "expected_keywords": ["next", "sentence", "isnext"],
    },
    {
        "id": "Q09",
        "query": "What GLUE, MultiNLI accuracy, and SQuAD F1 scores does BERT achieve after fine-tuning?",
        "expected_paper_id": "paper_devlin2019",
        "expected_keywords": ["glue", "squad", "multinli", "bert"],
    },
    {
        "id": "Q10",
        "query": "What is the architectural difference between BERT-Base and BERT-Large in layers, hidden size, and attention heads?",
        "expected_paper_id": "paper_devlin2019",
        "expected_keywords": ["bert", "layers", "hidden", "parameters"],
    },
    # paper_hu2021 (LoRA)
    {
        "id": "Q11",
        "query": "How does Low-Rank Adaptation (LoRA) freeze pre-trained weights and inject trainable rank decomposition matrices?",
        "expected_paper_id": "paper_hu2021",
        "expected_keywords": ["lora", "rank", "matrices", "weights"],
    },
    {
        "id": "Q12",
        "query": "How many times does LoRA reduce trainable parameters and GPU memory requirement on GPT-3 175B?",
        "expected_paper_id": "paper_hu2021",
        "expected_keywords": ["10,000", "gpt-3", "memory", "trainable"],
    },
    {
        "id": "Q13",
        "query": "Why does LoRA introduce no additional inference latency compared to adapter layers?",
        "expected_paper_id": "paper_hu2021",
        "expected_keywords": ["latency", "inference", "adapter", "lora"],
    },
    {
        "id": "Q14",
        "query": "How are the low-rank matrices A and B initialized in LoRA so delta W is zero at the start of training?",
        "expected_paper_id": "paper_hu2021",
        "expected_keywords": ["gaussian", "zero", "initialization"],
    },
    {
        "id": "Q15",
        "query": "Compare GPT-3 175B full fine-tuning versus LoRA on WikiSQL, MNLI-m, and SAMSum benchmarks.",
        "expected_paper_id": "paper_hu2021",
        "expected_keywords": ["wikisql", "samsum", "gpt-3", "lora"],
    },
    # paper_su2021 (RoFormer)
    {
        "id": "Q16",
        "query": "How does Rotary Position Embedding (RoPE) in RoFormer encode position with a rotation matrix?",
        "expected_paper_id": "paper_su2021",
        "expected_keywords": ["rotary", "rotation", "position", "rope"],
    },
    {
        "id": "Q17",
        "query": "How does RoPE incorporate explicit relative position dependency into the self-attention inner product?",
        "expected_paper_id": "paper_su2021",
        "expected_keywords": ["relative", "inner", "product", "rotary"],
    },
    {
        "id": "Q18",
        "query": "Why is Rotary Position Embedding compatible with linear attention and long-term decay?",
        "expected_paper_id": "paper_su2021",
        "expected_keywords": ["linear", "decay", "roformer", "rotary"],
    },
    {
        "id": "Q19",
        "query": "How does RoFormer generalize 2D rotation matrices in the complex plane to d-dimensional embeddings?",
        "expected_paper_id": "paper_su2021",
        "expected_keywords": ["complex", "matrix", "rotation", "2d"],
    },
    {
        "id": "Q20",
        "query": "How does RoFormer perform on GLUE benchmark tasks and long-text classification compared to BERT?",
        "expected_paper_id": "paper_su2021",
        "expected_keywords": ["roformer", "glue", "bert"],
    },
    # paper_dao2022 (FlashAttention)
    {
        "id": "Q21",
        "query": "How does FlashAttention use tiling and online softmax to avoid materializing the NxN attention matrix in GPU HBM?",
        "expected_paper_id": "paper_dao2022",
        "expected_keywords": ["flashattention", "tiling", "hbm", "sram"],
    },
    {
        "id": "Q22",
        "query": "How does FlashAttention reduce HBM memory accesses from O(N^2) to O(N) using on-chip SRAM?",
        "expected_paper_id": "paper_dao2022",
        "expected_keywords": ["hbm", "sram", "accesses", "memory"],
    },
    {
        "id": "Q23",
        "query": "Why does FlashAttention recompute the attention matrix during the backward pass instead of storing intermediate activations?",
        "expected_paper_id": "paper_dao2022",
        "expected_keywords": ["backward", "recomputation", "recompute", "sram"],
    },
    {
        "id": "Q24",
        "query": "What wall-clock training speedup does FlashAttention achieve on BERT-large, GPT-2, and Long-Range Arena?",
        "expected_paper_id": "paper_dao2022",
        "expected_keywords": ["flashattention", "gpt-2", "bert", "speedup"],
    },
    {
        "id": "Q25",
        "query": "How does block-sparse FlashAttention perform on Long-Range Arena Path-X and Path-256 sequences?",
        "expected_paper_id": "paper_dao2022",
        "expected_keywords": ["path-x", "long-range", "flashattention"],
    },
]


def _find_first_relevant_rank(candidates: List[Dict[str, Any]], expected_paper_id: str, top_k: int = 5) -> int:
    """Return 1-based rank (1..top_k) of first candidate matching expected_paper_id, or 0 if not in top_k."""
    for idx, item in enumerate(candidates[:top_k], start=1):
        chunk = item["chunk"]
        if chunk.paper_id == expected_paper_id:
            return idx
    return 0


def run_ir_benchmark(top_k: int = 5) -> Dict[str, Any]:
    """Execute the 25-question IR benchmark across BM25, Vector, Hybrid RRF, and Full Reranked pipelines."""
    ensure_corpus_indexed()
    # Pre-warm Bi-Encoder and Cross-Encoder weights so cold-start model loading is excluded from query latency
    get_bi_encoder()
    get_cross_encoder()

    total_q = len(BENCHMARK_QUESTIONS)
    bm25_rr_sum = 0.0
    vec_rr_sum = 0.0
    rrf_rr_sum = 0.0
    full_rr_sum = 0.0

    full_hit_at_1 = 0
    full_recall_at_k = 0
    latencies_ms: List[float] = []
    per_question_results: List[Dict[str, Any]] = []

    for q_spec in BENCHMARK_QUESTIONS:
        query_str = q_spec["query"]
        expected_pid = q_spec["expected_paper_id"]

        t0 = time.perf_counter()
        bm25_hits = bm25_index.search(query_str, top_k=20)
        vec_hits = vector_store.search(query_str, top_k=20)
        rrf_hits = reciprocal_rank_fusion(bm25_hits, vec_hits, k=60)
        reranked_hits = reranker.fuse_and_rerank(
            query=query_str,
            bm25_results=bm25_hits,
            vector_results=vec_hits,
            top_n=top_k,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        latencies_ms.append(elapsed_ms)

        r_bm25 = _find_first_relevant_rank(bm25_hits, expected_pid, top_k=top_k)
        r_vec = _find_first_relevant_rank(vec_hits, expected_pid, top_k=top_k)
        r_rrf = _find_first_relevant_rank(rrf_hits, expected_pid, top_k=top_k)
        r_full = _find_first_relevant_rank(reranked_hits, expected_pid, top_k=top_k)

        bm25_rr = (1.0 / r_bm25) if r_bm25 > 0 else 0.0
        vec_rr = (1.0 / r_vec) if r_vec > 0 else 0.0
        rrf_rr = (1.0 / r_rrf) if r_rrf > 0 else 0.0
        full_rr = (1.0 / r_full) if r_full > 0 else 0.0

        bm25_rr_sum += bm25_rr
        vec_rr_sum += vec_rr
        rrf_rr_sum += rrf_rr
        full_rr_sum += full_rr

        if r_full == 1:
            full_hit_at_1 += 1
        if r_full > 0:
            full_recall_at_k += 1

        top_score = float(reranked_hits[0]["relevance_score"]) if reranked_hits else 0.0
        per_question_results.append(
            {
                "id": q_spec["id"],
                "query": query_str,
                "expected_paper_id": expected_pid,
                "bm25_rank": r_bm25,
                "vector_rank": r_vec,
                "rrf_rank": r_rrf,
                "reranked_rank": r_full,
                "reciprocal_rank": round(full_rr, 4),
                "top_relevance_score": round(top_score, 4),
                "latency_ms": elapsed_ms,
            }
        )

    mrr_bm25 = round(bm25_rr_sum / total_q, 4)
    mrr_vec = round(vec_rr_sum / total_q, 4)
    mrr_rrf = round(rrf_rr_sum / total_q, 4)
    mrr_full = round(full_rr_sum / total_q, 4)
    mean_latency = round(sum(latencies_ms) / max(1, len(latencies_ms)), 2)
    max_latency = round(max(latencies_ms, default=0.0), 2)

    return {
        "total_questions": total_q,
        "top_k": top_k,
        "mrr_at_5": mrr_full,
        "target_mrr_at_5": 0.85,
        "passes_mrr_gate": mrr_full >= 0.85,
        "hit_rate_at_1": round(full_hit_at_1 / total_q, 4),
        "recall_at_5": round(full_recall_at_k / total_q, 4),
        "mean_retrieval_latency_ms": mean_latency,
        "max_retrieval_latency_ms": max_latency,
        "passes_latency_gate": mean_latency < 2000.0,
        "ablation": {
            "bm25_only_mrr_at_5": mrr_bm25,
            "vector_only_mrr_at_5": mrr_vec,
            "hybrid_rrf_mrr_at_5": mrr_rrf,
            "full_reranked_mrr_at_5": mrr_full,
        },
        "questions": per_question_results,
    }


def format_benchmark_markdown_table(summary: Dict[str, Any]) -> str:
    """Format the IR benchmark summary as a Markdown report table for Chapter 5."""
    ab = summary["ablation"]
    lines = [
        "### Quantitative Information Retrieval Benchmark Summary (25 Queries)",
        "",
        "| Pipeline Stage | MRR@5 | HitRate@1 | Recall@5 | Mean Latency (ms) | Gate Status |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
        f"| 1. Sparse BM25 Only | `{ab['bm25_only_mrr_at_5']:.4f}` | - | - | - | Baseline |",
        f"| 2. Dense Vector Only (`all-MiniLM-L6-v2`) | `{ab['vector_only_mrr_at_5']:.4f}` | - | - | - | Baseline |",
        f"| 3. Hybrid RRF (`k=60`) | `{ab['hybrid_rrf_mrr_at_5']:.4f}` | - | - | - | Intermediate |",
        (
            f"| **4. Full Hybrid + Cross-Encoder** | **`{summary['mrr_at_5']:.4f}`** | "
            f"**`{summary['hit_rate_at_1'] * 100:.1f}%`** | **`{summary['recall_at_5'] * 100:.1f}%`** | "
            f"**`{summary['mean_retrieval_latency_ms']:.2f} ms`** | "
            f"**{'PASS' if summary['passes_mrr_gate'] else 'FAIL'}** |"
        ),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    results = run_ir_benchmark(top_k=5)
    print(format_benchmark_markdown_table(results))

