"""Seed database initialization script to automatically index bundled seed papers on first boot (T045)."""

from backend.api.query_routes import ensure_corpus_indexed
from backend.rag.vector_store import vector_store
from backend.storage.db import db


def seed_if_needed(force: bool = False) -> dict:
    """Ensure the 5 seed papers are parsed and indexed into SQLite, ChromaDB, and BM25."""
    ensure_corpus_indexed(force_reingest=force)
    papers = db.list_papers()
    chunks_count = len(db.get_all_chunks())
    vectors_count = vector_store.count()
    summary = {
        "papers_indexed": len(papers),
        "chunks_indexed": chunks_count,
        "vectors_indexed": vectors_count,
        "paper_ids": [p.id for p in papers],
    }
    print(
        f"[SEED_DB] Ready: {summary['papers_indexed']} papers, "
        f"{summary['chunks_indexed']} SQLite chunks, "
        f"{summary['vectors_indexed']} ChromaDB vectors."
    )
    return summary


if __name__ == "__main__":
    seed_if_needed()

