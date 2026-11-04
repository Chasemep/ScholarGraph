"""Automated unit and integration tests for Phase 6 Document Ingestion & Spatial Parsing (T035):
Validates two-column extraction, section boundary categorization, Greek symbol & math notation
preservation, normalized bounding-box accuracy, and asynchronous /api/upload endpoints.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.parsers.pdf_parser import HierarchicalPDFParser, _detect_and_order_columns
from backend.parsers.text_cleaner import categorize_section_heading, clean_scientific_text
from backend.scripts.seed_pdfs_builder import SEED_PAPERS_MANIFEST, build_pdf_bytes
from backend.storage.db import db


def test_text_cleaner_preserves_greek_math_and_fixes_ligatures():
    """Verify clean_scientific_text expands ligatures, fixes line-wrap hyphens, and keeps Greek/math."""
    raw = (
        "We de\ufb01ne the e\ufb00ective weight update \u0394W = B\u00b7A scaled by \u03b1/r "
        "in a trans-\nformer with Self-Attention and low-rank matrices of complexity O(N^2)."
    )
    cleaned = clean_scientific_text(raw)
    assert "define" in cleaned
    assert "effective" in cleaned
    assert "transformer" in cleaned
    assert "Self-Attention" in cleaned
    assert "low-rank" in cleaned
    assert "\u0394W = B\u00b7A" in cleaned
    assert "\u03b1/r" in cleaned
    assert "O(N^2)" in cleaned
    assert clean_scientific_text("") == ""


@pytest.mark.parametrize(
    "line_input,expected_section",
    [
        ("Abstract", "Abstract"),
        ("[Abstract]", "Abstract"),
        ("1 Introduction", "Introduction"),
        ("I. INTRODUCTION", "Introduction"),
        ("2 Related Work", "Related Work"),
        ("3 Methods", "Methods"),
        ("3.2 Scaled Dot-Product Attention", "3.2 Scaled Dot-Product Attention"),
        ("4 Experiments", "Experiments"),
        ("5 Results and Discussion", "Results"),
        ("6 Conclusion", "Conclusion"),
        ("References", "References"),
        ("This is a regular sentence inside a paragraph.", None),
        ("128 256 512 91.4 88.2", None),
    ],
)
def test_section_boundary_categorization(line_input: str, expected_section: str | None):
    """Verify categorize_section_heading identifies canonical and numbered headings accurately."""
    assert categorize_section_heading(line_input) == expected_section


def test_two_column_layout_detection_orders_left_column_before_right_column():
    """Verify _detect_and_order_columns reads the entire left column top-to-bottom before the right column."""
    page_width = 612.0
    words = []

    # Create 20 words in left column (x: 50..260) at y = 150..340
    for i in range(20):
        words.append(
            {
                "text": f"LeftCol_{i}",
                "x0": 60.0 + (i % 2) * 50.0,
                "x1": 105.0 + (i % 2) * 50.0,
                "top": 150.0 + (i // 2) * 18.0,
                "bottom": 162.0 + (i // 2) * 18.0,
            }
        )
    # Create 20 words in right column (x: 330..540) at the SAME y = 150..340
    for i in range(20):
        words.append(
            {
                "text": f"RightCol_{i}",
                "x0": 340.0 + (i % 2) * 50.0,
                "x1": 395.0 + (i % 2) * 50.0,
                "top": 150.0 + (i // 2) * 18.0,
                "bottom": 162.0 + (i // 2) * 18.0,
            }
        )

    ordered_lines = _detect_and_order_columns(words, page_width)
    flattened_tokens = [w["text"] for line in ordered_lines for w in line]

    last_left_idx = max(idx for idx, tok in enumerate(flattened_tokens) if tok.startswith("LeftCol_"))
    first_right_idx = min(idx for idx, tok in enumerate(flattened_tokens) if tok.startswith("RightCol_"))
    assert last_left_idx < first_right_idx, "All left-column lines must precede right-column lines"


def test_hierarchical_pdf_parser_extracts_metadata_sections_and_bboxes(tmp_path: Path):
    """Verify HierarchicalPDFParser extracts metadata, section labels, and valid [page, x, y, w, h] bboxes."""
    sample_spec = SEED_PAPERS_MANIFEST[0]
    pdf_bytes = build_pdf_bytes(sample_spec)
    pdf_file = tmp_path / "vaswani_sample.pdf"
    pdf_file.write_bytes(pdf_bytes)

    parser = HierarchicalPDFParser(min_chunk_words=8)
    meta, chunks = parser.parse_pdf(pdf_file, paper_id_override="paper_test_vaswani")

    assert meta.id == "paper_test_vaswani"
    assert "Attention Is All You Need" in meta.title
    assert meta.total_pages == 3
    assert len(chunks) >= 3

    for ch in chunks:
        assert ch.paper_id == "paper_test_vaswani"
        assert ch.page_number >= 1
        assert ch.bbox.page == ch.page_number
        assert 0.0 <= ch.bbox.x <= 1.0
        assert 0.0 <= ch.bbox.y <= 1.0
        assert 0.0 < ch.bbox.width <= 1.0
        assert 0.0 < ch.bbox.height <= 1.0
        assert ch.token_count >= 8

    # Edge case: missing file raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        parser.parse_pdf(tmp_path / "does_not_exist.pdf")


def test_upload_endpoint_end_to_end_and_error_handling(api_client: TestClient):
    """Verify POST /api/upload, GET /api/upload/{task_id}, GET /api/upload, and invalid file rejection."""
    custom_spec = {
        "id": "paper_custom_upload",
        "filename": "custom_upload_test.pdf",
        "title": "Custom Uploaded Transformer Adapter Study",
        "authors": ["Jane Doe", "John Smith"],
        "year": 2025,
        "doi": "10.1000/custom.2025",
        "pages": [
            {
                "section": "Abstract",
                "paragraphs": [
                    "Custom Uploaded Transformer Adapter Study",
                    "Authors: Jane Doe, John Smith (2025)",
                    "Abstract: We propose a custom sparse adapter for Self-Attention layers in Transformer models, evaluated on the GLUE benchmark achieving 92.4% accuracy with minimal GPU memory.",
                ],
            }
        ],
    }
    pdf_bytes = build_pdf_bytes(custom_spec)

    # 1. Valid multipart PDF upload
    res = api_client.post(
        "/api/upload",
        files=[("files", ("custom_upload_test.pdf", pdf_bytes, "application/pdf"))],
    )
    assert res.status_code == 202
    tasks = res.json()
    assert len(tasks) == 1
    task_id = tasks[0]["task_id"]

    # 2. Poll task status (TestClient runs BackgroundTasks synchronously before returning)
    status_res = api_client.get(f"/api/upload/{task_id}")
    assert status_res.status_code == 200
    status_body = status_res.json()
    assert status_body["status"] == "ready"
    assert status_body["progress_percentage"] == 100
    ingested_paper_id = status_body["paper_id"]
    assert ingested_paper_id is not None

    # 3. Verify list upload tasks endpoint
    all_tasks_res = api_client.get("/api/upload")
    assert all_tasks_res.status_code == 200
    assert any(t["task_id"] == task_id for t in all_tasks_res.json())

    # Clean up uploaded test paper from database and storage
    try:
        del_res = api_client.delete(f"/api/documents/{ingested_paper_id}")
        assert del_res.status_code == 200
    except Exception:
        pass

    # 4. Edge Case: Non-PDF upload rejected with 400 Bad Request
    bad_res = api_client.post(
        "/api/upload",
        files=[("files", ("malicious.txt", b"NOT_A_PDF_FILE", "text/plain"))],
    )
    assert bad_res.status_code == 400

    # 5. Edge Case: Polling unknown task_id returns 404
    missing_task = api_client.get("/api/upload/task_nonexistent_000")
    assert missing_task.status_code == 404

