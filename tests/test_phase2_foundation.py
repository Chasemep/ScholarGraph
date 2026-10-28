"""Automated pytest suite verifying Phase 2 Foundational Infrastructure (T006-T011)."""

from pathlib import Path
from typing import List
import pdfplumber
import pypdf
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.main import app
from backend.models.paper import BoundingBox, IngestionStatus, PaperMetadata, TextChunk
from backend.rag.vector_store import VectorStoreManager
from backend.scripts.seed_pdfs_builder import SEED_PAPERS_MANIFEST, ensure_seed_pdfs
from backend.storage.db import DatabaseManager
from backend.storage.file_store import FileStoreManager


# ---------------------------------------------------------------------------
# T006: Pydantic v2 Data Models & Coordinate Constraints
# ---------------------------------------------------------------------------
def test_t006_bounding_box_valid_and_to_list():
    """Verify BoundingBox accepts valid normalized [page, x, y, width, height] coordinates."""
    bbox = BoundingBox(page=3, x=0.12, y=0.34, width=0.75, height=0.15)
    assert bbox.to_list() == [3, 0.12, 0.34, 0.75, 0.15]


@pytest.mark.parametrize(
    "invalid_kwargs",
    [
        {"page": 0, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5},      # page < 1
        {"page": -1, "x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5},     # negative page
        {"page": 1, "x": -0.01, "y": 0.1, "width": 0.5, "height": 0.5},    # x < 0
        {"page": 1, "x": 1.05, "y": 0.1, "width": 0.5, "height": 0.5},     # x > 1
        {"page": 1, "x": 0.1, "y": 0.1, "width": 0.0, "height": 0.5},      # width == 0
        {"page": 1, "x": 0.1, "y": 0.1, "width": 0.5, "height": 1.2},      # height > 1
    ],
)
def test_t006_bounding_box_rejects_out_of_range_coordinates(invalid_kwargs):
    """Edge case: BoundingBox must reject out-of-range coordinates or zero dimensions."""
    with pytest.raises(ValidationError):
        BoundingBox(**invalid_kwargs)


def test_t006_paper_metadata_and_text_chunk_validation():
    """Verify PaperMetadata and TextChunk validate non-empty strings and constraints."""
    paper = PaperMetadata(
        id="paper_vaswani2017",
        title="  Attention Is All You Need  ",
        authors=["Ashish Vaswani", "Noam Shazeer"],
        year=2017,
        filepath="data/papers/vaswani2017_attention.pdf",
        total_pages=15,
    )
    assert paper.title == "Attention Is All You Need"

    chunk = TextChunk(
        id="paper_vaswani2017_c0",
        paper_id="paper_vaswani2017",
        section="Abstract",
        page_number=1,
        bbox=BoundingBox(page=1, x=0.1, y=0.2, width=0.8, height=0.15),
        text="We propose a new simple network architecture, the Transformer.",
        token_count=10,
    )
    assert chunk.bbox.page == 1

    # Edge case: whitespace-only title or chunk text must raise ValidationError
    with pytest.raises(ValidationError):
        PaperMetadata(
            id="p1",
            title="   ",
            authors=[],
            filepath="data/papers/p1.pdf",
            total_pages=1,
        )
    with pytest.raises(ValidationError):
        TextChunk(
            id="c1",
            paper_id="p1",
            page_number=1,
            bbox=BoundingBox(page=1, x=0.1, y=0.1, width=0.5, height=0.2),
            text="   ",
            token_count=1,
        )

    status = IngestionStatus(
        task_id="task_1",
        filename="test.pdf",
        status="parsing",
        progress_percentage=40,
    )
    assert status.status == "parsing"


# ---------------------------------------------------------------------------
# T007: SQLite Database Manager, Schema Migrations & Cascade Integrity
# ---------------------------------------------------------------------------
def test_t007_sqlite_crud_and_cascade_delete(tmp_path: Path):
    """Verify SQLite table creation, paper/chunk CRUD, filtering, and ON DELETE CASCADE."""
    test_db = DatabaseManager(db_path=tmp_path / "test_scholar.db")
    assert test_db.check_health() is True

    paper = PaperMetadata(
        id="paper_test1",
        title="Test Transformer Architecture",
        authors=["Alice Smith", "Bob Jones"],
        year=2024,
        abstract="Sample abstract.",
        doi="10.1000/test.1",
        filepath="data/papers/test1.pdf",
        total_pages=5,
    )
    test_db.upsert_paper(paper)

    fetched = test_db.get_paper("paper_test1")
    assert fetched is not None
    assert fetched.title == "Test Transformer Architecture"
    assert fetched.authors == ["Alice Smith", "Bob Jones"]

    chunks = [
        TextChunk(
            id="paper_test1_c0",
            paper_id="paper_test1",
            section="Abstract",
            page_number=1,
            bbox=BoundingBox(page=1, x=0.1, y=0.1, width=0.8, height=0.2),
            text="First chunk text about self-attention.",
            token_count=6,
        ),
        TextChunk(
            id="paper_test1_c1",
            paper_id="paper_test1",
            section="Methods",
            page_number=2,
            bbox=BoundingBox(page=2, x=0.1, y=0.3, width=0.8, height=0.25),
            text="Second chunk text about low-rank adaptation.",
            token_count=7,
        ),
    ]
    saved_count = test_db.save_chunks(chunks)
    assert saved_count == 2

    paper_chunks = test_db.get_chunks_by_paper("paper_test1")
    assert len(paper_chunks) == 2
    assert paper_chunks[0].paper_title == "Test Transformer Architecture"
    assert paper_chunks[0].bbox.to_list() == [1, 0.1, 0.1, 0.8, 0.2]

    single = test_db.get_chunk_by_id("paper_test1_c1")
    assert single is not None
    assert single.section == "Methods"

    # Edge case: cascade delete paper removes its chunks automatically
    assert test_db.delete_paper("paper_test1") is True
    assert test_db.get_paper("paper_test1") is None
    assert test_db.get_chunks_by_paper("paper_test1") == []


# ---------------------------------------------------------------------------
# T008: Local PDF File Storage Repository Manager
# ---------------------------------------------------------------------------
def test_t008_file_store_persistence_and_security(tmp_path: Path):
    """Verify PDF byte validation, filename sanitization, and resolution."""
    store = FileStoreManager(base_dir=tmp_path / "papers")
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"

    saved_path = store.save_pdf_bytes("../../unsafe_name?!.pdf", valid_pdf)
    assert saved_path.parent == (tmp_path / "papers").resolve()
    assert saved_path.name == "unsafe_name__.pdf"

    resolved = store.resolve_pdf_path("unsafe_name__.pdf")
    assert resolved == saved_path
    assert len(store.list_stored_pdfs()) == 1

    # Edge case: non-PDF binary bytes rejected
    with pytest.raises(ValueError, match="Invalid PDF binary header"):
        store.save_pdf_bytes("corrupt.pdf", b"NOT_A_PDF_HEADER_12345")

    # Edge case: missing file raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        store.resolve_pdf_path("nonexistent_paper.pdf")

    assert store.delete_pdf("unsafe_name__.pdf") is True
    assert store.delete_pdf("unsafe_name__.pdf") is False


# ---------------------------------------------------------------------------
# T009: ChromaDB Persistent Vector Store & 384-d Embeddings
# ---------------------------------------------------------------------------
def _deterministic_mock_embedder(texts: List[str]) -> List[List[float]]:
    """Fast deterministic 384-d unit embedder for unit tests."""
    vectors: List[List[float]] = []
    for t in texts:
        tl = t.lower()
        vec = [0.0] * 384
        if "lora" in tl or "low-rank" in tl:
            vec[0] = 1.0
        elif "attention" in tl or "transformer" in tl:
            vec[1] = 1.0
        else:
            vec[2] = 1.0
        vectors.append(vec)
    return vectors


def test_t009_chromadb_vector_store_indexing_and_search(tmp_path: Path):
    """Verify ChromaDB collection indexing, 384-d constraint, and paper_id filtering."""
    vs = VectorStoreManager(
        persist_dir=tmp_path / "chroma",
        collection_name="test_scholar_chunks",
        embedding_fn=_deterministic_mock_embedder,
    )
    assert vs.check_health() is True
    assert vs.count() == 0

    chunks = [
        TextChunk(
            id="p_vaswani_c0",
            paper_id="paper_vaswani2017",
            paper_title="Attention Is All You Need",
            section="Abstract",
            page_number=1,
            bbox=BoundingBox(page=1, x=0.1, y=0.2, width=0.8, height=0.15),
            text="Scaled dot-product attention in the Transformer architecture.",
            token_count=8,
        ),
        TextChunk(
            id="p_hu_c0",
            paper_id="paper_hu2021",
            paper_title="LoRA: Low-Rank Adaptation",
            section="Methods",
            page_number=4,
            bbox=BoundingBox(page=4, x=0.12, y=0.35, width=0.76, height=0.14),
            text="LoRA injects low-rank adaptation matrices into frozen weights.",
            token_count=9,
        ),
    ]
    indexed = vs.index_chunks(chunks)
    assert indexed == 2
    assert vs.count() == 2

    hits = vs.search("How does LoRA low-rank adaptation work?", top_k=2)
    assert len(hits) == 2
    assert hits[0]["chunk"].id == "p_hu_c0"
    assert hits[0]["chunk"].bbox.page == 4
    assert hits[0]["score"] > hits[1]["score"]

    # Filter by paper_ids
    filtered = vs.search("attention", top_k=5, paper_ids=["paper_vaswani2017"])
    assert len(filtered) == 1
    assert filtered[0]["chunk"].paper_id == "paper_vaswani2017"

    # Delete paper chunks
    vs.delete_paper_chunks("paper_hu2021")
    assert vs.count() == 1


# ---------------------------------------------------------------------------
# T010: FastAPI Entrypoint & GET /api/health Endpoint
# ---------------------------------------------------------------------------
def test_t010_fastapi_health_endpoint():
    """Verify GET /api/health returns 200 OK and conforms to the REST API contract."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["version"] == "1.0.0"
    assert payload["sqlite_connected"] is True
    assert payload["chromadb_ready"] is True
    assert payload["embedding_model_loaded"] is True
    assert payload["cross_encoder_loaded"] is True
    assert payload["spacy_loaded"] is True
    assert isinstance(payload["gemini_api_configured"], bool)


# ---------------------------------------------------------------------------
# T011: Seed Collection of 5 High-Impact Open-Access Papers
# ---------------------------------------------------------------------------
def test_t011_seed_papers_bundled_and_parseable():
    """Verify all 5 seed papers exist in data/papers/ and extract words + bounding boxes."""
    paths = ensure_seed_pdfs()
    assert len(paths) == 5

    expected_filenames = {item["filename"] for item in SEED_PAPERS_MANIFEST}
    actual_filenames = {p.name for p in paths}
    assert actual_filenames == expected_filenames

    for pdf_path in paths:
        assert pdf_path.exists() and pdf_path.stat().st_size > 1000
        # Verify pypdf page count
        reader = pypdf.PdfReader(str(pdf_path))
        assert len(reader.pages) >= 3, f"{pdf_path.name} should have at least 3 pages"

        # Verify pdfplumber word + bounding-box coordinate extraction
        with pdfplumber.open(str(pdf_path)) as pdf:
            words = pdf.pages[0].extract_words()
            assert len(words) > 30, f"{pdf_path.name} page 1 should contain extractable words"
            first_word = words[0]
            assert 0 <= first_word["x0"] < first_word["x1"] <= pdf.pages[0].width
            assert 0 <= first_word["top"] < first_word["bottom"] <= pdf.pages[0].height

