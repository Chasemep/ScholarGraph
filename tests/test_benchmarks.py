"""Automated verification tests for Phase 8 IR Benchmark Harness and API Endpoint (T047-T048)."""

from backend.benchmarks.evaluate_rag import (
    BENCHMARK_QUESTIONS,
    format_benchmark_markdown_table,
    run_ir_benchmark,
)


def test_t047_benchmark_dataset_and_mrr_gate():
    """Verify the 25-question IR benchmark dataset achieves MRR@5 >= 0.85 and mean latency < 2000ms."""
    assert len(BENCHMARK_QUESTIONS) == 25
    summary = run_ir_benchmark(top_k=5)
    assert summary["total_questions"] == 25
    assert summary["mrr_at_5"] >= 0.85, f"Expected MRR@5 >= 0.85, got {summary['mrr_at_5']}"
    assert summary["passes_mrr_gate"] is True
    assert summary["mean_retrieval_latency_ms"] < 2000.0
    assert summary["passes_latency_gate"] is True

    md_table = format_benchmark_markdown_table(summary)
    assert "MRR@5" in md_table
    assert "PASS" in md_table


def test_t048_benchmark_api_route(api_client):
    """Verify GET /api/benchmarks/run returns 200 OK with valid MRR@5 and per-question metrics."""
    res = api_client.get("/api/benchmarks/run")
    assert res.status_code == 200
    data = res.json()
    assert data["total_questions"] == 25
    assert data["mrr_at_5"] >= 0.85
    assert data["passes_mrr_gate"] is True
    assert len(data["questions"]) == 25

