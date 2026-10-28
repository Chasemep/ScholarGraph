"""Asynchronous & background PDF ingestion pipeline with staged status tracking (T039)."""

import uuid
from typing import Dict, List
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from backend.models.paper import IngestionStatus
from backend.parsers.pdf_parser import pdf_parser
from backend.rag.bm25_index import bm25_index
from backend.rag.vector_store import vector_store
from backend.storage.db import db
from backend.storage.file_store import file_store

router = APIRouter(prefix="/api", tags=["Document Ingestion"])

# In-memory registry tracking ingestion task progress
INGESTION_TASKS: Dict[str, IngestionStatus] = {}


def process_pdf_ingestion_task(task_id: str, filename: str, content: bytes) -> None:
    """Execute staged PDF ingestion: Save -> Parse coordinates -> Embed in ChromaDB -> Rebuild BM25."""
    try:
        INGESTION_TASKS[task_id] = IngestionStatus(
            task_id=task_id,
            filename=filename,
            status="parsing",
            progress_percentage=30,
        )

        saved_path = file_store.save_pdf_bytes(filename, content)
        paper_meta, chunks = pdf_parser.parse_pdf(saved_path)

        INGESTION_TASKS[task_id] = IngestionStatus(
            task_id=task_id,
            paper_id=paper_meta.id,
            filename=filename,
            status="embedding",
            progress_percentage=70,
        )

        db.upsert_paper(paper_meta)
        db.save_chunks(chunks)

        if chunks:
            batch_size = 100
            for i in range(0, len(chunks), batch_size):
                vector_store.index_chunks(chunks[i : i + batch_size])

        # Synchronize lexical BM25 index
        bm25_index.build_index(db.get_all_chunks())

        INGESTION_TASKS[task_id] = IngestionStatus(
            task_id=task_id,
            paper_id=paper_meta.id,
            filename=filename,
            status="ready",
            progress_percentage=100,
        )
    except Exception as exc:
        INGESTION_TASKS[task_id] = IngestionStatus(
            task_id=task_id,
            filename=filename,
            status="failed",
            progress_percentage=100,
            error_message=str(exc),
        )


@router.post("/upload", status_code=202, response_model=List[IngestionStatus])
async def upload_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
) -> List[IngestionStatus]:
    """Upload one or more scientific PDF documents for parsing, coordinate tracking, and indexing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    statuses: List[IngestionStatus] = []
    for upload in files:
        fname = upload.filename or "uploaded_paper.pdf"
        raw_bytes = await upload.read()

        if not file_store.validate_pdf_bytes(raw_bytes):
            raise HTTPException(
                status_code=400,
                detail=f"File '{fname}' is not a valid PDF document (missing %PDF- header).",
            )

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        initial_status = IngestionStatus(
            task_id=task_id,
            filename=fname,
            status="parsing",
            progress_percentage=25,
        )
        INGESTION_TASKS[task_id] = initial_status
        background_tasks.add_task(process_pdf_ingestion_task, task_id, fname, raw_bytes)
        statuses.append(initial_status)

    return statuses


@router.get("/upload/{task_id}", response_model=IngestionStatus)
def get_upload_task_status(task_id: str) -> IngestionStatus:
    """Poll the current status of an asynchronous PDF ingestion task."""
    if task_id not in INGESTION_TASKS:
        raise HTTPException(status_code=404, detail=f"Ingestion task '{task_id}' not found.")
    return INGESTION_TASKS[task_id]


@router.get("/upload", response_model=List[IngestionStatus])
def list_upload_tasks() -> List[IngestionStatus]:
    """Return all tracked PDF ingestion tasks."""
    return list(INGESTION_TASKS.values())

