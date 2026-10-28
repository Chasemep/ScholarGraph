"""Centralized application configuration using Pydantic v2 BaseSettings."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API & LLM Configuration
    gemini_api_key: str = Field(default="", description="Google Gemini API key for grounded synthesis")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Default Gemini model identifier")

    # Server Configuration
    host: str = Field(default="127.0.0.1", description="FastAPI bind host")
    port: int = Field(default=8000, description="FastAPI bind port")
    frontend_port: int = Field(default=5173, description="Frontend Vite dev server port")

    # Storage Paths
    papers_dir: Path = Field(
        default=PROJECT_ROOT / "data" / "papers",
        description="Directory storing ingested PDF binaries",
    )
    chroma_dir: Path = Field(
        default=PROJECT_ROOT / "data" / "chromadb",
        description="Directory storing ChromaDB persistent index",
    )
    sqlite_path: Path = Field(
        default=PROJECT_ROOT / "data" / "sqlite" / "scholargraph.db",
        description="Path to SQLite relational database file",
    )

    # Retrieval Hyperparameters
    bm25_top_k: int = Field(default=20, description="Top-K sparse BM25 candidates")
    vector_top_k: int = Field(default=20, description="Top-K dense ChromaDB candidates")
    rrf_k: int = Field(default=60, description="Reciprocal Rank Fusion constant k")
    rerank_top_n: int = Field(default=5, description="Top-N Cross-Encoder passages passed to synthesis")
    min_relevance_threshold: float = Field(
        default=0.25,
        description="Minimum normalized relevance threshold before triggering out-of-scope refusal",
    )


settings = Settings()

