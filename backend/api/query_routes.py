"""FastAPI routes for Hybrid RAG querying, document listing, and PDF binary streaming."""

import re
import time
from pathlib import Path
from typing import List, Optional

import pdfplumber
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.config import settings
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

            words = page.extract_words(
                x_tolerance=1.5,
                y_tolerance=3.0,
                keep_blank_chars=False,
            )
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
        seed_paths = ensure_seed_pdfs(force_arxiv_download=False)
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
def list_documents() -> List[PaperMetadata]:
    """List all indexed scientific papers in the repository."""
    ensure_corpus_indexed()
    return db.list_papers()


@router.get("/documents/{paper_id}/pdf")
def stream_paper_pdf(paper_id: str) -> FileResponse:
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
def delete_document(paper_id: str) -> dict:
    """Delete an indexed paper and its chunks from SQLite, ChromaDB, and BM25."""
    paper = db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper with ID '{paper_id}' not found.")

    db.delete_paper(paper_id)
    vector_store.delete_paper_chunks(paper_id)
    bm25_index.build_index(db.get_all_chunks())
    return {"deleted": True, "paper_id": paper_id}



# ---------------------------------------------------------------------------
# Query understanding: comparative / formula / follow-up intent detection
# ---------------------------------------------------------------------------

COMPARATIVE_QUERY_REGEX = re.compile(
    r"\b(?:differen\w*|differ|compar\w*|contrast\w*|versus|vs\.?|distinguish\w*|similarit\w*|"
    r"relat\w* to each other|each (?:paper|model|approach|method|version|variant|one)|"
    r"every (?:paper|model|version|variant)|versions?|variants?|all (?:three|two|four|\d+)|"
    r"the (?:two|three|four|five|\d+) (?:\S+ )?(?:papers|models|approaches|methods|variants|versions)|"
    r"between (?:the|these)|across)\b",
    re.IGNORECASE,
)

FORMULA_QUERY_REGEX = re.compile(
    r"\b(?:formula\w*|equation\w*|governing|expression\w*|mathematical(?:ly)? (?:form|model|definition)|"
    r"system of|ode|odes|dde|pde|define[ds]?|definition\w*|written as|update rule|dynamics)\b",
    re.IGNORECASE,
)

FOLLOWUP_QUERY_REGEX = re.compile(
    r"^(?:and|also|ok(?:ay)?|so|now|then|just|only|what about|how about|same|instead)\b|"
    r"\b(?:them|those|these|they|their|it|its|that|this one|the same|above|previous|earlier|you mentioned|"
    r"each of them|each one|the formulas|the equations|the models|the papers)\b",
    re.IGNORECASE,
)

BOILERPLATE_REGEX = re.compile(
    r"(?:contents lists available|journal homepage|www\.\w+|elsevier|springer|all rights reserved|"
    r"received:? \d|accepted:? \d|published online|doi:? ?10\.|©|\bcopyright\b|issn|"
    r"mathematical society of japan|j\. math\. anal\. appl\.)",
    re.IGNORECASE,
)

MATH_SIGNAL_REGEX = re.compile(r"(=|\bdt\b|d[xv]\b|∑|Σ|α|β|τ|ξ|η|γ|δ|∥|≤|≥|→|\(\d{1,2}\))")


def _is_comparative_query(query: str) -> bool:
    return bool(COMPARATIVE_QUERY_REGEX.search(query or ""))


def _is_formula_query(query: str) -> bool:
    return bool(FORMULA_QUERY_REGEX.search(query or ""))


def _is_followup_query(query: str, history: list) -> bool:
    if not history:
        return False
    q = (query or "").strip()
    return bool(FOLLOWUP_QUERY_REGEX.search(q)) or len(q.split()) <= 7


def _is_boilerplate_chunk(chunk: TextChunk) -> bool:
    """Journal headers, copyright lines, title/author-only blocks carry no scientific content."""
    text = chunk.text or ""
    words = text.split()
    if BOILERPLATE_REGEX.search(text) and len(words) < 60:
        return True
    # Title / author block: short, mostly capitalised words, no sentence punctuation
    if len(words) < 25 and not re.search(r"[.;:]\s", text):
        return True
    return False


def _math_density(text: str) -> float:
    if not text:
        return 0.0
    hits = len(MATH_SIGNAL_REGEX.findall(text))
    return hits / max(1.0, len(text.split()) ** 0.5)


MODEL_DEFINITION_CUES = re.compile(
    r"(?:model reads|our model|the model is|is governed by|governed by the|the dynamic|system of (?:ordinary )?"
    r"differential equations|is given by|takes the (?:following )?(?:form|format)|we (?:introduce|propose|consider) "
    r"(?:the|a|our)|the corresponding model|original formulation|modified (?:\w+[- ])?model|\bd[xv]\b[^.]{0,40}\bdt\b|"
    r"\b[xv] ?\(t ?\+ ?h\))",
    re.IGNORECASE,
)
PROOF_CUES = re.compile(r"\b(?:proof|lemma|hence|therefore|contraction|banach|≤ .* ≤|we obtain|it follows)\b", re.I)


def _model_definition_score(chunk: TextChunk) -> float:
    """Prefer passages that *state* a model's equations over dense proof/estimate passages."""
    text = chunk.text or ""
    density = min(_math_density(text), 2.0)
    cues = len(MODEL_DEFINITION_CUES.findall(text))
    proof = len(PROOF_CUES.findall(text))
    early = 0.6 if chunk.page_number <= 3 else 0.0
    return density + 1.5 * min(cues, 3) - 0.6 * min(proof, 3) + early


def _contextualize_query(query: str, history: list, api_key: Optional[str]) -> str:
    """Rewrite a follow-up question into a standalone retrieval query using conversation history."""
    if not history:
        return query

    prior_user = [t.content for t in history if t.role == "user" and t.content.strip()]
    if not prior_user:
        return query

    key = (api_key or settings.gemini_api_key or "").strip()
    if key and key != "LOCAL_FALLBACK":
        convo = "\n".join(
            f"{t.role.upper()}: {t.content[:600]}" for t in history[-6:] if t.content.strip()
        )
        prompt = (
            "Rewrite the FINAL user question into a single standalone search query that includes all "
            "subjects it refers to from the conversation (paper names, model names, topics). "
            "Return ONLY the rewritten query, no explanation.\n\n"
            f"CONVERSATION:\n{convo}\n\nFINAL USER QUESTION: {query}\n\nSTANDALONE QUERY:"
        )
        rewritten = generator.quick_completion(prompt, key)
        if rewritten and 3 <= len(rewritten) <= 400:
            return rewritten.strip().strip('"')

    # Deterministic fallback: prepend the most recent prior user question
    return f"{prior_user[-1]} {query}"


def _paper_group_lookup() -> dict:
    """Map paper_id -> (group_id, subgroup_id) using the knowledge graph's topic hierarchy."""
    from backend.graph.graph_builder import graph_builder

    lookup: dict = {}
    for _nid, attrs in graph_builder.graph.nodes(data=True):
        if attrs.get("type") != "Paper":
            continue
        meta = attrs.get("metadata", {}) or {}
        pid = meta.get("paper_id")
        if pid:
            lookup[pid] = (meta.get("group_id"), meta.get("subgroup_id"))
    return lookup


def _select_relevant_papers(
    top_ranked: List[dict],
    focus_paper_ids: List[str],
    paper_ids_filter: Optional[List[str]],
    max_papers: int,
) -> List[str]:
    """Pick the papers a multi-paper answer must cover.

    = papers carried over from the previous answer (follow-ups)
    + the strongest papers in the current retrieval
    + their Category/Subcategory mates in the knowledge graph (same subject).
    """
    from backend.api.graph_routes import _rebuild_graph_from_db

    try:
        _rebuild_graph_from_db()
        group_lookup = _paper_group_lookup()
    except Exception:
        group_lookup = {}

    paper_strength: dict = {}
    for cand in top_ranked:
        pid = cand["chunk"].paper_id
        paper_strength[pid] = max(paper_strength.get(pid, 0.0), float(cand.get("relevance_score", 0.0)))

    strong = [
        pid
        for pid, s in sorted(paper_strength.items(), key=lambda kv: kv[1], reverse=True)
        if s >= settings.min_relevance_threshold
    ]

    relevant: List[str] = []
    for pid in focus_paper_ids:
        if pid not in relevant:
            relevant.append(pid)
    for pid in strong[:2]:
        if pid not in relevant:
            relevant.append(pid)

    anchor = relevant[0] if relevant else None
    anchor_group = group_lookup.get(anchor, (None, None)) if anchor else (None, None)
    if anchor_group[0]:
        key_idx = 1 if anchor_group[1] else 0
        for pid, grp in group_lookup.items():
            if grp[key_idx] == anchor_group[key_idx] and pid not in relevant:
                relevant.append(pid)
    for pid in strong:
        if pid not in relevant and paper_strength[pid] >= settings.min_relevance_threshold + 0.15:
            relevant.append(pid)

    if paper_ids_filter:
        allowed = set(paper_ids_filter)
        relevant = [pid for pid in relevant if pid in allowed]
    return relevant[:max_papers]


def _gather_per_paper_evidence(
    query: str,
    relevant: List[str],
    formula_mode: bool,
    per_paper: int = 3,
) -> List[dict]:
    """Collect balanced, content-bearing evidence from each relevant paper."""
    all_chunks = db.get_all_chunks(paper_ids=relevant)
    chunks_by_paper: dict = {}
    for ch in all_chunks:
        chunks_by_paper.setdefault(ch.paper_id, []).append(ch)

    floor = settings.min_relevance_threshold + 0.05
    expanded: List[dict] = []
    seen: set = set()

    def _add(chunk: TextChunk, score: float) -> None:
        if chunk.id in seen or _is_boilerplate_chunk(chunk):
            return
        seen.add(chunk.id)
        expanded.append({"chunk": chunk, "relevance_score": round(max(score, floor), 4)})

    for pid in relevant:
        ordered = sorted(
            chunks_by_paper.get(pid, []),
            key=lambda c: (c.page_number, int(re.sub(r"\D", "", c.id.rsplit("_c", 1)[-1]) or 0)),
        )
        index_of = {c.id: i for i, c in enumerate(ordered)}

        # 1) Abstract / opening passages: what the paper is about and what it changes
        opening = [
            c for c in ordered
            if (c.section or "").lower() in {"abstract", "introduction"} and not _is_boilerplate_chunk(c)
        ][:2]
        for c in opening:
            _add(c, floor)

        # 2) Model-definition passages: math-dense chunks on the first pages (+ the following chunk,
        #    because equations and their explanation are often split across chunk boundaries)
        early = [c for c in ordered if c.page_number <= 5 and _math_density(c.text) >= 0.6]
        math_ranked = sorted(early, key=_model_definition_score, reverse=True)
        n_math = 4 if formula_mode else 2
        for c in math_ranked[:n_math]:
            _add(c, floor + 0.05)
            nxt_i = index_of[c.id] + 1
            if formula_mode and nxt_i < len(ordered):
                _add(ordered[nxt_i], floor)

        # 3) The paper's passages that best match the question itself
        p_bm25 = bm25_index.search(query=query, top_k=10, paper_ids=[pid])
        p_vec = vector_store.search(query=query, top_k=10, paper_ids=[pid])
        for cand in reranker.fuse_and_rerank(
            query=query, bm25_results=p_bm25, vector_results=p_vec, top_n=per_paper
        ):
            _add(cand["chunk"], float(cand.get("relevance_score", 0.0)))

    return expanded


@router.post("/query", response_model=QueryResponse)
def query_literature(request: QueryRequest) -> QueryResponse:
    """Execute Hybrid BM25 + ChromaDB retrieval, RRF fusion, Cross-Encoder re-ranking, and grounded synthesis."""
    ensure_corpus_indexed()

    t0 = time.perf_counter()
    history = request.history[-8:] if request.history else []

    # Resolve follow-ups ("just give me the formulas") against the conversation
    is_followup = _is_followup_query(request.query, history)
    retrieval_query = (
        _contextualize_query(request.query, history, request.api_key) if is_followup else request.query
    )
    focus_paper_ids: List[str] = []
    if is_followup:
        for turn in reversed(history):
            if turn.role == "assistant" and turn.paper_ids:
                focus_paper_ids = list(dict.fromkeys(turn.paper_ids))
                break

    bm25_hits = bm25_index.search(query=retrieval_query, top_k=20, paper_ids=request.paper_ids)
    vector_hits = vector_store.search(query=retrieval_query, top_k=20, paper_ids=request.paper_ids)

    is_comparative = _is_comparative_query(retrieval_query) or _is_comparative_query(request.query)
    is_formula = _is_formula_query(request.query) or _is_formula_query(retrieval_query)
    multi_paper_mode = is_comparative or is_formula or bool(focus_paper_ids)

    effective_top_k = max(request.top_k, 8) if multi_paper_mode else request.top_k
    top_ranked = reranker.fuse_and_rerank(
        query=retrieval_query,
        bm25_results=bm25_hits,
        vector_results=vector_hits,
        top_n=effective_top_k,
    )
    top_ranked = [c for c in top_ranked if not _is_boilerplate_chunk(c["chunk"])] or top_ranked

    if multi_paper_mode:
        relevant = _select_relevant_papers(
            top_ranked,
            focus_paper_ids,
            request.paper_ids,
            max_papers=6 if (is_comparative or focus_paper_ids) else 3,
        )
        if relevant:
            evidence = _gather_per_paper_evidence(retrieval_query, relevant, formula_mode=is_formula)
            if evidence:
                top_ranked = evidence
    t_retrieval_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    t1 = time.perf_counter()
    gen_out = generator.generate(
        query=request.query,
        ranked_candidates=top_ranked,
        api_key_override=request.api_key,
        comparative=is_comparative,
        formula_mode=is_formula,
        history=history,
        retrieval_query=retrieval_query,
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
