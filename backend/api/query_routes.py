"""FastAPI routes for Hybrid RAG querying, document listing, and PDF binary streaming."""

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


def extract_seed_chunks_from_pdf(paper_spec: dict, pdf_path: Path) -> List[TextChunk]:
    """Extract paragraph chunks with normalized pdfplumber bounding boxes from a seed PDF."""
    chunks: List[TextChunk] = []
    chunk_counter = 0

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            page_num = page_idx + 1
            page_w = float(page.width or 612.0)
            page_h = float(page.height or 792.0)
            section_name = (
                paper_spec["pages"][page_idx]["section"]
                if page_idx < len(paper_spec.get("pages", []))
                else f"Page {page_num}"
            )

            words = page.extract_words(keep_blank_chars=False)
            if not words:
                continue

            # Group words into paragraphs by vertical gap (> 16pt gap starts a new paragraph block)
            paragraphs: List[List[dict]] = []
            current_group: List[dict] = []
            last_bottom: float | None = None

            for w in words:
                top = float(w["top"])
                bottom = float(w["bottom"])
                if last_bottom is not None and (top - last_bottom) > 16.0 and current_group:
                    paragraphs.append(current_group)
                    current_group = [w]
                else:
                    current_group.append(w)
                last_bottom = bottom
            if current_group:
                paragraphs.append(current_group)

            for group in paragraphs:
                text_str = " ".join(w["text"] for w in group).strip()
                # Skip short section title brackets like "[Abstract]"
                if len(text_str) < 25 or (text_str.startswith("[") and text_str.endswith("]")):
                    continue

                x0 = max(0.0, min(w["x0"] for w in group) / page_w)
                y0 = max(0.0, min(w["top"] for w in group) / page_h)
                x1 = min(1.0, max(w["x1"] for w in group) / page_w)
                y1 = min(1.0, max(w["bottom"] for w in group) / page_h)

                width = max(0.05, min(1.0 - x0, x1 - x0))
                height = max(0.02, min(1.0 - y0, y1 - y0))

                chunks.append(
                    TextChunk(
                        id=f"{paper_spec['id']}_c{chunk_counter}",
                        paper_id=paper_spec["id"],
                        paper_title=paper_spec["title"],
                        section=section_name,
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

    return chunks


def ensure_corpus_indexed() -> None:
    """Ensure SQLite, ChromaDB, and in-memory BM25 index are populated and synchronized."""
    existing_papers = db.list_papers()
    if not existing_papers:
        seed_paths = ensure_seed_pdfs()
        path_by_name = {p.name: p for p in seed_paths}
        all_new_chunks: List[TextChunk] = []

        for spec in SEED_PAPERS_MANIFEST:
            pdf_path = path_by_name[spec["filename"]]
            rel_path = file_store.get_relative_filepath(pdf_path)
            abstract_text = spec["pages"][0]["paragraphs"][2] if len(spec["pages"][0]["paragraphs"]) > 2 else ""
            paper_meta = PaperMetadata(
                id=spec["id"],
                title=spec["title"],
                authors=spec["authors"],
                year=spec["year"],
                abstract=abstract_text,
                doi=spec["doi"],
                filepath=rel_path,
                total_pages=len(spec["pages"]),
            )
            db.upsert_paper(paper_meta)
            paper_chunks = extract_seed_chunks_from_pdf(spec, pdf_path)
            db.save_chunks(paper_chunks)
            all_new_chunks.extend(paper_chunks)

        if all_new_chunks:
            vector_store.index_chunks(all_new_chunks)

    all_db_chunks = db.get_all_chunks()
    if len(bm25_index.chunks) != len(all_db_chunks):
        bm25_index.build_index(all_db_chunks)
    if vector_store.count() == 0 and all_db_chunks:
        vector_store.index_chunks(all_db_chunks)


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

    # Step 1: Dual retrieval (BM25 sparse + ChromaDB dense)
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

    # Step 2: Reciprocal Rank Fusion (k=60) + Cross-Encoder Re-Ranking
    top_ranked = reranker.fuse_and_rerank(
        query=request.query,
        bm25_results=bm25_hits,
        vector_results=vector_hits,
        top_n=request.top_k,
    )
    t_retrieval_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    # Step 3: Grounded Synthesis (Gemini API or deterministic extractive fallback)
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

