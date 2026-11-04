"""FastAPI route for executing the 25-question Information Retrieval benchmark suite (T048)."""

from typing import Any, Dict
from fastapi import APIRouter

from backend.benchmarks.evaluate_rag import run_ir_benchmark

router = APIRouter(prefix="/api/benchmarks", tags=["Benchmarks"])


@router.get("/run")
def execute_rag_benchmark(top_k: int = 5) -> Dict[str, Any]:
    """Run the 25-question IR evaluation suite and return MRR@5, HitRate@1, Recall@5, and latency metrics."""
    return run_ir_benchmark(top_k=top_k)

