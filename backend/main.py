"""FastAPI application entrypoint, CORS middleware, exception handlers, and /api/health probe."""

import importlib.util
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.query_routes import router as query_router
from backend.config import settings
from backend.rag.vector_store import vector_store
from backend.storage.db import db

app = FastAPI(
    title="ScholarGraph API",
    description="Grounded Scientific Literature Exploration & Knowledge Graph Platform",
    version="1.0.0",
)

app.include_router(query_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        f"http://localhost:{settings.frontend_port}",
        f"http://127.0.0.1:{settings.frontend_port}",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(_request: Request, exc: FileNotFoundError) -> JSONResponse:
    """Return 404 JSON response when a requested file or paper PDF is missing."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    """Return 400 JSON response for domain validation errors."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def _check_package_available(pkg_name: str) -> bool:
    return importlib.util.find_spec(pkg_name) is not None


@app.get("/api/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Readiness healthcheck endpoint per REST API contract."""
    sqlite_ok = db.check_health()
    chroma_ok = vector_store.check_health()
    st_ok = _check_package_available("sentence_transformers")
    spacy_ok = _check_package_available("spacy")
    gemini_ok = bool(settings.gemini_api_key and settings.gemini_api_key.strip())

    overall_healthy = sqlite_ok and chroma_ok and st_ok and spacy_ok
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "version": "1.0.0",
        "sqlite_connected": sqlite_ok,
        "chromadb_ready": chroma_ok,
        "embedding_model_loaded": st_ok,
        "cross_encoder_loaded": st_ok,
        "spacy_loaded": spacy_ok,
        "gemini_api_configured": gemini_ok,
    }

