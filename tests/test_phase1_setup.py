"""Automated tests verifying Phase 1 Setup (T001-T005)."""

import json
from pathlib import Path
from backend.config import PROJECT_ROOT, Settings, settings


def test_t001_directory_structure_exists():
    """Verify all required Tier 1-4 directories exist per plan.md."""
    required_dirs = [
        "backend/api",
        "backend/benchmarks",
        "backend/graph",
        "backend/models",
        "backend/parsers",
        "backend/rag",
        "backend/scripts",
        "backend/storage",
        "frontend/src/components",
        "frontend/src/services",
        "data/papers",
        "data/chromadb",
        "data/sqlite",
        "tests",
    ]
    for rel_path in required_dirs:
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists() and full_path.is_dir(), f"Missing directory: {rel_path}"


def test_t002_backend_requirements_manifest():
    """Verify backend/requirements.txt lists all mandatory packages."""
    req_file = PROJECT_ROOT / "backend" / "requirements.txt"
    assert req_file.exists(), "backend/requirements.txt does not exist"
    content = req_file.read_text(encoding="utf-8").lower()
    expected_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic-settings",
        "pypdf",
        "pdfplumber",
        "sentence-transformers",
        "chromadb",
        "rank-bm25",
        "spacy",
        "networkx",
        "google-generativeai",
        "pytest",
        "pytest-cov",
        "httpx",
    ]
    for pkg in expected_packages:
        assert pkg in content, f"Missing required package '{pkg}' in backend/requirements.txt"


def test_t003_frontend_manifest_and_tailwind():
    """Verify frontend/package.json and frontend/tailwind.config.js are configured."""
    pkg_file = PROJECT_ROOT / "frontend" / "package.json"
    tailwind_file = PROJECT_ROOT / "frontend" / "tailwind.config.js"
    assert pkg_file.exists(), "frontend/package.json does not exist"
    assert tailwind_file.exists(), "frontend/tailwind.config.js does not exist"

    pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
    deps = pkg_data.get("dependencies", {})
    for required_dep in ["react", "cytoscape", "cytoscape-cola", "pdfjs-dist", "lucide-react", "axios"]:
        assert required_dep in deps, f"Missing frontend dependency '{required_dep}'"


def test_t004_download_models_script_exists():
    """Verify backend/scripts/download_models.py exists and defines model constants."""
    from backend.scripts import download_models

    assert download_models.SPACY_MODEL == "en_core_web_sm"
    assert download_models.BI_ENCODER_MODEL == "all-MiniLM-L6-v2"
    assert download_models.CROSS_ENCODER_MODEL == "cross-encoder/ms-marco-MiniLM-L-6-v2"


def test_t005_config_settings_loads():
    """Verify backend/config.py initializes Pydantic BaseSettings properly."""
    assert isinstance(settings, Settings)
    assert settings.port == 8000
    assert settings.rrf_k == 60
    assert settings.rerank_top_n == 5
    assert settings.papers_dir == PROJECT_ROOT / "data" / "papers"
    assert settings.chroma_dir == PROJECT_ROOT / "data" / "chromadb"
    assert settings.sqlite_path == PROJECT_ROOT / "data" / "sqlite" / "scholargraph.db"

    # Test environment override behavior
    custom = Settings(port=9001, rrf_k=50, gemini_api_key="test-key-123")
    assert custom.port == 9001
    assert custom.rrf_k == 50
    assert custom.gemini_api_key == "test-key-123"

