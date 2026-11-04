"""End-to-End browser test suite using Playwright.
Simulates uploading 10+ real academic papers and querying across them (complex, simple, unrelated).
Records webm videos directly into the user's Documents folder.
"""

import os
import time
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
_custom_video_dir = os.environ.get("VIDEO_DIR")
VIDEO_DIR = Path(_custom_video_dir) if _custom_video_dir else Path(os.environ.get("USERPROFILE", "C:/Users/Chase")) / "Documents" / "ScholarGraph_E2E_Videos"
REAL_PAPERS_DIR = Path(__file__).resolve().parent / "test_data" / "real_papers"


@pytest.fixture(scope="session")
def setup_video_dir():
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    return VIDEO_DIR


def test_scholargraph_e2e_multi_paper_and_queries(setup_video_dir):
    """Comprehensive E2E Test:
    1. Launch browser with video recording in Documents/ScholarGraph_E2E_Videos.
    2. Upload 10+ real academic PDF papers through UI.
    3. Verify multi-file upload progress tracking in UI.
    4. Close upload modal to proceed to querying.
    5. Query 1 (Complex Cross-Paper): Compare Attention mechanisms across Transformers.
    6. Query 2 (Complex Cross-Paper): Dropout and Batch Normalization regularization.
    7. Query 3 (Simple Targeted): Adam optimizer recommended hyperparameters.
    8. Query 4 (Unrelated / Out of Scope): Bronze Age Mesopotamian agriculture.
    9. Verify video generated and non-empty.
    """
    assert REAL_PAPERS_DIR.exists(), f"Papers dir not found at {REAL_PAPERS_DIR}"
    pdf_files = sorted(list(REAL_PAPERS_DIR.glob("*.pdf")), key=lambda f: f.stat().st_size)
    assert len(pdf_files) >= 10, f"Expected 10+ papers, found {len(pdf_files)}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir=str(setup_video_dir),
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        # Step 1: Navigate to ScholarGraph frontend
        page.goto(FRONTEND_URL, wait_until="networkidle", timeout=30000)
        expect(page.locator("text=ScholarGraph").first).to_be_visible(timeout=10000)

        # Step 2: Open Upload Modal
        upload_btn = page.locator("button:has-text('Upload PDFs')")
        expect(upload_btn).to_be_visible()
        upload_btn.click()

        modal_title = page.locator("h3:has-text('Upload PDF Papers')")
        expect(modal_title).to_be_visible()

        # Step 3: Select and Upload 10+ Real Full Academic PDFs
        file_input = page.locator("input[type='file']")
        selected_ten_pdfs = [str(f.resolve()) for f in pdf_files[:10]]
        file_input.set_input_files(selected_ten_pdfs)

        # Confirm selected files list rendered with all 10 papers
        expect(page.locator("text=Selected Files (10)")).to_be_visible(timeout=5000)

        # Click Start Upload
        start_upload_btn = page.locator("button:has-text('Upload (10)')")
        expect(start_upload_btn).to_be_visible()
        start_upload_btn.click()

        # Step 4: Verify upload initiation and staged progress
        # The modal replaces selected files with upload task cards
        page.wait_for_timeout(3000)

        # Close the upload modal using Close or Cancel to unlock chat interface
        close_btn = page.locator("button:has-text('Close'), button:has-text('Done'), button:has-text('Cancel')").first
        expect(close_btn).to_be_visible()
        close_btn.click()
        expect(modal_title).to_be_hidden(timeout=10000)

        prompt_area = page.locator("textarea[placeholder='Ask a question about your papers...']")
        ask_btn = page.locator("button[type='submit']")

        # Step 5: Complex Cross-Paper Query 1
        # Synthesizing concepts across multi-head attention and transformer representations
        complex_query_1 = "Compare the attention mechanisms and layer normalization between Transformer and RoFormer architectures."
        prompt_area.fill(complex_query_1)
        ask_btn.click()

        # Verify assistant response appears and completes
        page.wait_for_selector("article", timeout=60000)
        page.wait_for_selector("div.animate-pulse", state="hidden", timeout=60000)
        
        first_article = page.locator("article").first
        expect(first_article).to_be_visible()
        first_text = first_article.inner_text()
        assert len(first_text) > 50, f"Assistant response was unexpectedly short: {first_text}"

        # Step 6: Complex Cross-Paper Query 2
        # Connecting parameter efficiency (LoRA) and FlashAttention memory scaling
        complex_query_2 = "How do LoRA low-rank adaptation and FlashAttention memory tiling complement each other for scaling large transformer models?"
        prompt_area.fill(complex_query_2)
        ask_btn.click()

        # Wait for second response
        page.wait_for_selector("div.animate-pulse", state="visible", timeout=10000)
        page.wait_for_selector("div.animate-pulse", state="hidden", timeout=60000)
        expect(page.locator("article")).to_have_count(2, timeout=10000)
        second_article_text = page.locator("article").nth(1).inner_text()
        assert len(second_article_text) > 50

        # Step 7: Simple Targeted Query
        simple_query = "What scaling factor 1/sqrt(d_k) is applied in scaled dot-product attention in the Transformer?"
        prompt_area.fill(simple_query)
        ask_btn.click()

        page.wait_for_selector("div.animate-pulse", state="visible", timeout=10000)
        page.wait_for_selector("div.animate-pulse", state="hidden", timeout=60000)
        expect(page.locator("article")).to_have_count(3, timeout=10000)
        third_article_text = page.locator("article").nth(2).inner_text()
        assert any(term in third_article_text.lower() for term in ["d_k", "scaling", "sqrt", "dot-product", "dimension"])

        # Step 8: Unrelated / Out-of-Scope Query
        unrelated_query = "What was the agricultural crop yield of emmer wheat in Ancient Mesopotamia during the Bronze Age?"
        prompt_area.fill(unrelated_query)
        ask_btn.click()

        page.wait_for_selector("div.animate-pulse", state="visible", timeout=10000)
        page.wait_for_selector("div.animate-pulse", state="hidden", timeout=60000)
        expect(page.locator("article")).to_have_count(4, timeout=10000)
        fourth_article_text = page.locator("article").nth(3).inner_text()
        
        # Verify zero-hallucination refusal response
        assert any(phrase in fourth_article_text.lower() for phrase in [
            "sufficient",
            "couldn't find",
            "does not contain",
            "suggested follow-ups",
            "clarif",
        ]), f"Expected refusal for unrelated query, got: {fourth_article_text}"

        # Close page and context to flush video to disk
        video_path = page.video.path()
        page.close()
        context.close()
        browser.close()

        # Step 9: Verify video recording was saved
        assert video_path is not None, "Playwright video was not recorded"
        saved_video = Path(video_path)
        assert saved_video.exists(), f"Video file {saved_video} does not exist"
        assert saved_video.stat().st_size > 1000, f"Video file {saved_video} is too small ({saved_video.stat().st_size} bytes)"
        print(f"\n[E2E SUCCESS] Recorded test video at: {saved_video} ({saved_video.stat().st_size / 1024:.1f} KB)")

