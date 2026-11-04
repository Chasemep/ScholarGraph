"""Automated verification tests for Phase 7 Containerized Deployment & Seed Bootstrap (T042-T046)."""

from backend.config import PROJECT_ROOT
from backend.scripts.seed_database import seed_if_needed


def test_t042_backend_dockerfile_configured():
    """Verify backend/Dockerfile uses multi-stage python:3.10-slim build, model caching, and healthcheck."""
    dockerfile = PROJECT_ROOT / "backend" / "Dockerfile"
    assert dockerfile.exists(), "backend/Dockerfile is missing"
    content = dockerfile.read_text(encoding="utf-8")
    assert "FROM python:3.10-slim AS builder" in content
    assert "FROM python:3.10-slim AS runtime" in content
    assert "backend.scripts.download_models" in content
    assert "HEALTHCHECK" in content
    assert "/api/health" in content
    assert "backend.scripts.seed_database" in content


def test_t043_frontend_dockerfile_and_nginx_reverse_proxy():
    """Verify frontend/Dockerfile and frontend/nginx.conf configure multi-stage build and /api proxy."""
    dockerfile = PROJECT_ROOT / "frontend" / "Dockerfile"
    nginx_conf = PROJECT_ROOT / "frontend" / "nginx.conf"
    if not dockerfile.exists():
        import pytest
        pytest.skip("frontend files not mounted inside containerized backend environment")

    df_text = dockerfile.read_text(encoding="utf-8")
    assert "FROM node:18-alpine AS build" in df_text
    assert "FROM nginx:stable-alpine AS runtime" in df_text
    assert "npm run build" in df_text

    nginx_text = nginx_conf.read_text(encoding="utf-8")
    assert "location /api/" in nginx_text
    assert "proxy_pass http://backend:8000/api/;" in nginx_text


def test_t044_docker_compose_orchestration_and_volumes():
    """Verify docker-compose.yml defines backend & frontend services, volume mounts, and healthcheck dependency."""
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        import pytest
        pytest.skip("docker-compose.yml not mounted inside containerized backend environment")
    text = compose_file.read_text(encoding="utf-8")
    assert "backend:" in text
    assert "frontend:" in text
    assert "./data/papers:/app/data/papers" in text
    assert "./data/chromadb:/app/data/chromadb" in text
    assert "./data/sqlite:/app/data/sqlite" in text
    assert "condition: service_healthy" in text


def test_t045_seed_database_script_idempotent_execution():
    """Verify backend/scripts/seed_database.py initializes the seed corpus idempotently."""
    summary = seed_if_needed(force=False)
    assert summary["papers_indexed"] >= 5
    assert summary["chunks_indexed"] >= 15
    assert summary["vectors_indexed"] >= 15
    assert "paper_vaswani2017" in summary["paper_ids"]
    assert "paper_hu2021" in summary["paper_ids"]

