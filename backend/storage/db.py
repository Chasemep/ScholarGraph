"""SQLite database connection manager, schema migrations, and repository methods."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional

from backend.config import settings
from backend.models.paper import BoundingBox, PaperMetadata, TextChunk


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT NOT NULL,
    year INTEGER,
    abstract TEXT,
    doi TEXT,
    filepath TEXT NOT NULL,
    total_pages INTEGER NOT NULL CHECK (total_pages >= 1),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_chunks (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    section TEXT NOT NULL,
    page_number INTEGER NOT NULL CHECK (page_number >= 1),
    bbox_x REAL NOT NULL CHECK (bbox_x >= 0.0 AND bbox_x <= 1.0),
    bbox_y REAL NOT NULL CHECK (bbox_y >= 0.0 AND bbox_y <= 1.0),
    bbox_w REAL NOT NULL CHECK (bbox_w > 0.0 AND bbox_w <= 1.0),
    bbox_h REAL NOT NULL CHECK (bbox_h > 0.0 AND bbox_h <= 1.0),
    text TEXT NOT NULL,
    token_count INTEGER NOT NULL CHECK (token_count >= 1),
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_paper_id ON paper_chunks(paper_id);
CREATE INDEX IF NOT EXISTS idx_chunks_page ON paper_chunks(paper_id, page_number);
"""


class DatabaseManager:
    """Manages SQLite relational persistence for paper metadata and text chunks."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else Path(settings.sqlite_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a SQLite connection with foreign keys enabled and Row factory set."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Execute table and index creation migrations."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)

    def check_health(self) -> bool:
        """Verify SQLite connection and schema readiness."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('papers', 'paper_chunks');"
                )
                tables = {row["name"] for row in cursor.fetchall()}
                return {"papers", "paper_chunks"}.issubset(tables)
        except Exception:
            return False

    def upsert_paper(self, paper: PaperMetadata) -> PaperMetadata:
        """Insert or update a paper metadata record."""
        created_iso = (
            paper.created_at.isoformat()
            if isinstance(paper.created_at, datetime)
            else str(paper.created_at)
        )
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO papers (id, title, authors, year, abstract, doi, filepath, total_pages, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    authors = excluded.authors,
                    year = excluded.year,
                    abstract = excluded.abstract,
                    doi = excluded.doi,
                    filepath = excluded.filepath,
                    total_pages = excluded.total_pages
                """,
                (
                    paper.id,
                    paper.title,
                    json.dumps(paper.authors),
                    paper.year,
                    paper.abstract,
                    paper.doi,
                    paper.filepath,
                    paper.total_pages,
                    created_iso,
                ),
            )
        return paper

    def get_paper(self, paper_id: str) -> Optional[PaperMetadata]:
        """Retrieve a single paper by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
            if not row:
                return None
            return self._row_to_paper(row)

    def list_papers(self) -> List[PaperMetadata]:
        """Return all papers ordered by creation time descending."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM papers ORDER BY created_at DESC, id ASC").fetchall()
            return [self._row_to_paper(r) for r in rows]

    def delete_paper(self, paper_id: str) -> bool:
        """Delete a paper and cascade-delete its chunks."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
            return cursor.rowcount > 0

    def save_chunks(self, chunks: List[TextChunk]) -> int:
        """Batch insert or replace text chunks for a paper."""
        if not chunks:
            return 0
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO paper_chunks (
                    id, paper_id, section, page_number,
                    bbox_x, bbox_y, bbox_w, bbox_h,
                    text, token_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        c.id,
                        c.paper_id,
                        c.section,
                        c.page_number,
                        c.bbox.x,
                        c.bbox.y,
                        c.bbox.width,
                        c.bbox.height,
                        c.text,
                        c.token_count,
                    )
                    for c in chunks
                ],
            )
        return len(chunks)

    def get_chunks_by_paper(self, paper_id: str) -> List[TextChunk]:
        """Retrieve all chunks belonging to a specific paper."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT c.*, p.title AS paper_title
                FROM paper_chunks c
                JOIN papers p ON c.paper_id = p.id
                WHERE c.paper_id = ?
                ORDER BY c.page_number ASC, c.id ASC
                """,
                (paper_id,),
            ).fetchall()
            return [self._row_to_chunk(r) for r in rows]

    def get_chunk_by_id(self, chunk_id: str) -> Optional[TextChunk]:
        """Retrieve a single chunk by its ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT c.*, p.title AS paper_title
                FROM paper_chunks c
                JOIN papers p ON c.paper_id = p.id
                WHERE c.id = ?
                """,
                (chunk_id,),
            ).fetchone()
            return self._row_to_chunk(row) if row else None

    def get_all_chunks(self, paper_ids: Optional[List[str]] = None) -> List[TextChunk]:
        """Retrieve all chunks in the database, optionally filtered by paper_ids."""
        with self.get_connection() as conn:
            if paper_ids:
                placeholders = ",".join("?" for _ in paper_ids)
                query = f"""
                    SELECT c.*, p.title AS paper_title
                    FROM paper_chunks c
                    JOIN papers p ON c.paper_id = p.id
                    WHERE c.paper_id IN ({placeholders})
                    ORDER BY c.paper_id ASC, c.page_number ASC, c.id ASC
                """
                rows = conn.execute(query, tuple(paper_ids)).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT c.*, p.title AS paper_title
                    FROM paper_chunks c
                    JOIN papers p ON c.paper_id = p.id
                    ORDER BY c.paper_id ASC, c.page_number ASC, c.id ASC
                    """
                ).fetchall()
            return [self._row_to_chunk(r) for r in rows]

    @staticmethod
    def _row_to_paper(row: sqlite3.Row) -> PaperMetadata:
        created_raw = row["created_at"]
        try:
            created_dt = datetime.fromisoformat(created_raw)
        except ValueError:
            created_dt = datetime.now(timezone.utc)
        return PaperMetadata(
            id=row["id"],
            title=row["title"],
            authors=json.loads(row["authors"]) if row["authors"] else [],
            year=row["year"],
            abstract=row["abstract"],
            doi=row["doi"],
            filepath=row["filepath"],
            total_pages=row["total_pages"],
            created_at=created_dt,
        )

    @staticmethod
    def _row_to_chunk(row: sqlite3.Row) -> TextChunk:
        return TextChunk(
            id=row["id"],
            paper_id=row["paper_id"],
            paper_title=row["paper_title"] if "paper_title" in row.keys() else None,
            section=row["section"],
            page_number=row["page_number"],
            bbox=BoundingBox(
                page=row["page_number"],
                x=row["bbox_x"],
                y=row["bbox_y"],
                width=row["bbox_w"],
                height=row["bbox_h"],
            ),
            text=row["text"],
            token_count=row["token_count"],
        )


db = DatabaseManager()

