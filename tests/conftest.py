"""Shared pytest fixtures, mock Gemini API responses, and isolated test databases (T031)."""

from pathlib import Path
from typing import Any, Callable, List
import pytest

try:
    from fastapi.testclient import TestClient

    from backend.main import app
    from backend.models.paper import BoundingBox, PaperMetadata, TextChunk
    from backend.rag.bm25_index import BM25IndexManager
    from backend.rag.vector_store import VectorStoreManager
    from backend.storage.db import DatabaseManager
    from backend.storage.file_store import FileStoreManager
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False
    TestClient = None  # type: ignore
    app = None  # type: ignore
    BoundingBox = None  # type: ignore
    PaperMetadata = None  # type: ignore
    TextChunk = None  # type: ignore
    BM25IndexManager = None  # type: ignore
    VectorStoreManager = None  # type: ignore
    DatabaseManager = None  # type: ignore
    FileStoreManager = None  # type: ignore


def deterministic_384d_embedder(texts: List[str]) -> List[List[float]]:
    """Fast deterministic 384-dimensional unit vector embedder for isolated tests."""
    vectors: List[List[float]] = []
    for text in texts:
        tl = text.lower()
        vec = [0.0] * 384
        if "lora" in tl or "low-rank" in tl or "10,000" in tl:
            vec[0] = 1.0
        elif "attention" in tl or "transformer" in tl or "sqrt" in tl:
            vec[1] = 1.0
        elif "flashattention" in tl or "sram" in tl or "hbm" in tl:
            vec[2] = 1.0
        elif "bert" in tl or "masked" in tl:
            vec[3] = 1.0
        elif "rope" in tl or "roformer" in tl or "rotary" in tl:
            vec[4] = 1.0
        else:
            vec[5] = 1.0
        vectors.append(vec)
    return vectors


@pytest.fixture
def isolated_db(tmp_path: Path) -> Any:
    """Provide an isolated temporary SQLite DatabaseManager instance."""
    if not HAS_BACKEND or DatabaseManager is None:
        pytest.skip("backend dependencies not installed in current environment")
    return DatabaseManager(db_path=tmp_path / "isolated_scholar.db")


@pytest.fixture
def isolated_file_store(tmp_path: Path) -> Any:
    """Provide an isolated temporary FileStoreManager directory."""
    if not HAS_BACKEND or FileStoreManager is None:
        pytest.skip("backend dependencies not installed in current environment")
    return FileStoreManager(base_dir=tmp_path / "isolated_papers")


@pytest.fixture
def isolated_vector_store(tmp_path: Path) -> Any:
    """Provide an isolated ChromaDB VectorStoreManager with deterministic 384-d embeddings."""
    if not HAS_BACKEND or VectorStoreManager is None:
        pytest.skip("backend dependencies not installed in current environment")
    return VectorStoreManager(
        persist_dir=tmp_path / "isolated_chroma",
        collection_name="isolated_scholar_chunks",
        embedding_fn=deterministic_384d_embedder,
    )


@pytest.fixture
def isolated_bm25() -> Any:
    """Provide a fresh in-memory BM25IndexManager."""
    if not HAS_BACKEND or BM25IndexManager is None:
        pytest.skip("backend dependencies not installed in current environment")
    return BM25IndexManager()


@pytest.fixture
def sample_papers() -> List[Any]:
    """Provide reusable PaperMetadata fixtures."""
    if not HAS_BACKEND or PaperMetadata is None:
        pytest.skip("backend dependencies not installed in current environment")
    return [
        PaperMetadata(
            id="paper_vaswani2017",
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer"],
            year=2017,
            abstract="We propose the Transformer architecture based solely on Self-Attention.",
            doi="10.48550/arXiv.1706.03762",
            filepath="data/papers/vaswani2017_attention.pdf",
            total_pages=15,
        ),
        PaperMetadata(
            id="paper_hu2021",
            title="LoRA: Low-Rank Adaptation of Large Language Models",
            authors=["Edward J. Hu", "Yelong Shen"],
            year=2021,
            abstract="We propose LoRA to freeze pre-trained weights and inject low-rank matrices.",
            doi="10.48550/arXiv.2106.09685",
            filepath="data/papers/hu2021_lora.pdf",
            total_pages=26,
        ),
    ]


@pytest.fixture
def sample_chunks() -> List[Any]:
    """Provide reusable spatial TextChunk fixtures with valid BoundingBox coordinates."""
    if not HAS_BACKEND or TextChunk is None:
        pytest.skip("backend dependencies not installed in current environment")
    return [
        TextChunk(
            id="paper_vaswani2017_c0",
            paper_id="paper_vaswani2017",
            paper_title="Attention Is All You Need",
            section="Scaled Dot-Product Attention",
            page_number=4,
            bbox=BoundingBox(page=4, x=0.10, y=0.20, width=0.80, height=0.15),
            text="Scaled Dot-Product Attention computes dot products of queries and keys divided by sqrt(d_k) on WMT 2014 achieving 28.4 BLEU.",
            token_count=20,
        ),
        TextChunk(
            id="paper_hu2021_c0",
            paper_id="paper_hu2021",
            paper_title="LoRA: Low-Rank Adaptation of Large Language Models",
            section="Low-Rank Parameterized Update Matrices",
            page_number=4,
            bbox=BoundingBox(page=4, x=0.12, y=0.35, width=0.76, height=0.14),
            text="Following Vaswani et al. (2017), LoRA injects low-rank matrices into Self-Attention layers, reducing trainable parameters by 10,000 times and GPU memory by 3-fold on GLUE and WikiSQL.",
            token_count=28,
        ),
    ]


@pytest.fixture
def mock_gemini_callable() -> Callable[[str, str, str], str]:
    """Provide a deterministic mock Gemini LLM callable returning grounded inline citations."""
    def _mock_llm(_system_prompt: str, user_prompt: str, _api_key: str) -> str:
        if "quantum annealing" in user_prompt.lower():
            return "The ingested literature does not contain sufficient evidence to answer this query."
        return (
            "LoRA freezes pre-trained weights and injects low-rank matrices into Self-Attention "
            "layers, reducing trainable parameters by 10,000 times [paper_hu2021, Page 4], "
            "building upon the Scaled Dot-Product Attention introduced in the Transformer "
            "[paper_vaswani2017, Page 4]."
        )

    return _mock_llm


@pytest.fixture
def api_client() -> Any:
    """Provide a FastAPI TestClient wired to the main ScholarGraph application."""
    if not HAS_BACKEND or TestClient is None:
        pytest.skip("backend dependencies not installed in current environment")
    return TestClient(app)

