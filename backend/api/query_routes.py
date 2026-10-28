"""FastAPI routes for Hybrid RAG querying, document listing, and PDF binary streaming."""

import re
import time
from pathlib import Path
from typing import List

import pdfplumber
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.models.paper import BoundingBox, PaperMetadata, TextChunk
from backend.models.rag import QueryRequest, QueryResponse
from backend.rag.bm25_index import bm25_index
from backend.rag.generator import generator
from backend.rag.reranker import reranker
from backend.rag.vector_store import vector_store
from backend.scripts.seed_pdfs_builder import SEED_PAPERS_MANIFEST, ensure_seed_pdfs
from backend.storage.db import db
from backend.storage.file_store import file_store

router = APIRouter(prefix="/api", tags=["RAG & Documents"])

SECTION_HEADING_REGEX = re.compile(
    r"^(?:abstract|introduction|related work|background|method(?:s|ology)?|model architecture|"
    r"experiments?|empirical evaluation|results?|discussion|conclusion(?:s)?|"
    r"\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9\s\-:]{2,50})$",
    re.IGNORECASE,
)


def extract_seed_chunks_from_pdf(paper_spec: dict, pdf_path: Path) -> tuple[List[TextChunk], int]:
    """Extract section-aware text chunks with normalized pdfplumber bounding boxes from a PDF."""
    chunks: List[TextChunk] = []
    chunk_counter = 0

    with pdfplumber.open(str(pdf_path)) as pdf:
        total_pages = len(pdf.pages)
        current_section = "Abstract"

        for page_idx, page in enumerate(pdf.pages):
            page_num = page_idx + 1
            page_w = float(page.width or 612.0)
            page_h = float(page.height or 792.0)

            words = page.extract_words(keep_blank_chars=False)
            if not words:
                continue

            # First group words into visual lines (words within 4pt vertical tolerance)
            lines: List[List[dict]] = []
            cur_line: List[dict] = []
            last_top: float | None = None

            for w in words:
                top = float(w["top"])
                if last_top is not None and abs(top - last_top) > 4.5 and cur_line:
                    lines.append(cur_line)
                    cur_line = [w]
                else:
                    cur_line.append(w)
                last_top = top
            if cur_line:
                lines.append(cur_line)

            # Group lines into coherent paragraphs / passage blocks (~80 - 220 words)
            current_block_words: List[dict] = []
            current_block_word_count = 0
            prev_line_bottom: float | None = None

            def _flush_block(block_words: List[dict], sec_name: str) -> None:
                nonlocal chunk_counter
                if not block_words:
                    return
                text_str = " ".join(w["text"] for w in block_words).strip()
                # Clean hyphenated line-breaks common in two-column arXiv PDFs
                text_str = re.sub(r"(\w)-\s+(\w)", r"\1\2", text_str)
                if len(text_str) < 45:
                    return

                x0 = max(0.0, min(float(w["x0"]) for w in block_words) / page_w)
                y0 = max(0.0, min(float(w["top"]) for w in block_words) / page_h)
                x1 = min(1.0, max(float(w["x1"]) for w in block_words) / page_w)
                y1 = min(1.0, max(float(w["bottom"]) for w in block_words) / page_h)

                width = max(0.05, min(1.0 - x0, x1 - x0))
                height = max(0.02, min(1.0 - y0, y1 - y0))

                chunks.append(
                    TextChunk(
                        id=f"{paper_spec['id']}_c{chunk_counter}",
                        paper_id=paper_spec["id"],
                        paper_title=paper_spec["title"],
                        section=sec_name,
                        page_number=page_num,
                        bbox=BoundingBox(
                            page=page_num,
                            x=round(x0, 4),
                            y=round(y0, 4),
                            width=round(width, 4),
                            height=round(height, 4),
                        ),
                        text=text_str,
                        token_count=max(1, len(text_str.split())),
                    )
                )
                chunk_counter += 1

            for line in lines:
                line_text = " ".join(w["text"] for w in line).strip()
                line_top = min(float(w["top"]) for w in line)
                line_bottom = max(float(w["bottom"]) for w in line)

                # Detect section headings
                cleaned_heading = line_text.strip("[]")
                if len(cleaned_heading) <= 60 and SECTION_HEADING_REGEX.match(cleaned_heading):
                    _flush_block(current_block_words, current_section)
                    current_block_words = []
                    current_block_word_count = 0
                    current_section = cleaned_heading
                    prev_line_bottom = line_bottom
                    continue

                # Start a new paragraph chunk if vertical gap > 10pt and block already has >= 75 words,
                # or if block exceeds 190 words
                vertical_gap = (line_top - prev_line_bottom) if prev_line_bottom is not None else 0.0
                if (
                    (vertical_gap > 10.0 and current_block_word_count >= 75)
                    or current_block_word_count + len(line) > 190
                ):
                    _flush_block(current_block_words, current_section)
                    current_block_words = list(line)
                    current_block_word_count = len(line)
                else:
                    current_block_words.extend(line)
                    current_block_word_count += len(line)

                prev_line_bottom = line_bottom

            _flush_block(current_block_words, current_section)

    return chunks, total_pages


def ensure_corpus_indexed(force_reingest: bool = False) -> None:
    """Ensure SQLite, ChromaDB, and in-memory BM25 index are populated and synchronized."""
    existing_papers = db.list_papers()
    if force_reingest or not existing_papers:
        seed_paths = ensure_seed_pdfs(force_arxiv_download=force_reingest)
        path_by_name = {p.name: p for p in seed_paths}
        all_new_chunks: List[TextChunk] = []

        for spec in SEED_PAPERS_MANIFEST:
            if force_reingest:
                db.delete_paper(spec["id"])
                vector_store.delete_paper_chunks(spec["id"])

            pdf_path = path_by_name[spec["filename"]]
            rel_path = file_store.get_relative_filepath(pdf_path)
            abstract_text = (
                spec["pages"][0]["paragraphs"][2]
                if len(spec["pages"][0]["paragraphs"]) > 2
                else ""
            )
            paper_chunks, actual_pages = extract_seed_chunks_from_pdf(spec, pdf_path)

            paper_meta = PaperMetadata(
                id=spec["id"],
                title=spec["title"],
                authors=spec["authors"],
                year=spec["year"],
                abstract=abstract_text,
                doi=spec["doi"],
                filepath=rel_path,
                total_pages=max(1, actual_pages),
            )
            db.upsert_paper(paper_meta)
            db.save_chunks(paper_chunks)
            all_new_chunks.extend(paper_chunks)

        if all_new_chunks:
            # Index in batches of 100 to keep memory footprint smooth
            batch_size = 100
            for i in range(0, len(all_new_chunks), batch_size):
                vector_store.index_chunks(all_new_chunks[i : i + batch_size])

        bm25_index.build_index(db.get_all_chunks())
        return

    all_db_chunks = db.get_all_chunks()
    if len(bm25_index.chunks) != len(all_db_chunks):
        bm25_index.build_index(all_db_chunks)
    if vector_store.count() == 0 and all_db_chunks:
        batch_size = 100
        for i in range(0, len(all_db_chunks), batch_size):
            vector_store.index_chunks(all_db_chunks[i : i + batch_size])


@router.get("/documents", response_model=List[PaperMetadata])
async def list_documents() -> List[PaperMetadata]:
    """List all indexed scientific papers in the repository."""
    ensure_corpus_indexed()
    return db.list_papers()


@router.get("/documents/{paper_id}/pdf")
async def stream_paper_pdf(paper_id: str) -> FileResponse:
    """Stream the binary PDF file for a given paper_id to the PDF.js reader."""
    ensure_corpus_indexed()
    paper = db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper with ID '{paper_id}' not found.")

    try:
        pdf_path = file_store.resolve_pdf_path(paper.filepath)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@router.delete("/documents/{paper_id}")
async def delete_document(paper_id: str) -> dict:
    """Delete an indexed paper and its chunks from SQLite, ChromaDB, and BM25."""
    paper = db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper with ID '{paper_id}' not found.")

    db.delete_paper(paper_id)
    vector_store.delete_paper_chunks(paper_id)
    bm25_index.build_index(db.get_all_chunks())
    return {"deleted": True, "paper_id": paper_id}


@router.post("/query", response_model=QueryResponse)
async def query_literature(request: QueryRequest) -> QueryResponse:
    """Execute Hybrid BM25 + ChromaDB retrieval, RRF fusion, Cross-Encoder re-ranking, and grounded synthesis."""
    ensure_corpus_indexed()

    t0 = time.perf_counter()

    bm25_hits = bm25_index.search(
        query=request.query,
        top_k=20,
        paper_ids=request.paper_ids,
    )
    vector_hits = vector_store.search(
        query=request.query,
        top_k=20,
        paper_ids=request.paper_ids,
    )

    top_ranked = reranker.fuse_and_rerank(
        query=request.query,
        bm25_results=bm25_hits,
        vector_results=vector_hits,
        top_n=request.top_k,
    )
    t_retrieval_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    t1 = time.perf_counter()
    gen_out = generator.generate(
        query=request.query,
        ranked_candidates=top_ranked,
        api_key_override=request.api_key,
    )
    t_synthesis_ms = round((time.perf_counter() - t1) * 1000.0, 2)

    return QueryResponse(
        query=request.query,
        answer=gen_out["answer"],
        status=gen_out["status"],
        citations=gen_out["citations"],
        model_used=gen_out["model_used"],
        retrieval_latency_ms=t_retrieval_ms,
        synthesis_latency_ms=t_synthesis_ms,
    )
