"""Hierarchical PDF parser and section-aware spatial chunker using pdfplumber and pypdf (T037).

Supports single-column and two-column scientific layouts, extracts bibliographic metadata,
and computes normalized paragraph bounding-box coordinates [page, x, y, width, height].
"""

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber
import pypdf

from backend.models.paper import BoundingBox, PaperMetadata, TextChunk
from backend.parsers.text_cleaner import categorize_section_heading, clean_scientific_text
from backend.storage.file_store import file_store


def _detect_and_order_columns(words: List[Dict[str, Any]], page_width: float) -> List[List[Dict[str, Any]]]:
    """Detect whether a page uses a two-column layout and return ordered visual lines.

    In two-column academic papers, words in the left column (x1 <= midpoint + margin)
    must be read top-to-bottom before words in the right column (x0 >= midpoint - margin),
    while full-width headers/titles at the top span across the midpoint.
    """
    if not words:
        return []

    midpoint = page_width / 2.0
    gutter_tol = page_width * 0.03

    header_words: List[Dict[str, Any]] = []
    left_words: List[Dict[str, Any]] = []
    right_words: List[Dict[str, Any]] = []
    spanning_words: List[Dict[str, Any]] = []

    for w in words:
        x0 = float(w["x0"])
        x1 = float(w["x1"])
        top = float(w["top"])

        # Top 18% of page 1 or full-width spanning lines
        if x1 <= midpoint + gutter_tol:
            left_words.append(w)
        elif x0 >= midpoint - gutter_tol:
            right_words.append(w)
        else:
            if top < page_width * 0.28:
                header_words.append(w)
            else:
                spanning_words.append(w)

    total = len(words)
    # Consider page two-column if both left and right halves each contain >= 20% of the page's words
    is_two_column = (
        total >= 30
        and len(left_words) >= total * 0.20
        and len(right_words) >= total * 0.20
        and len(spanning_words) <= total * 0.25
    )

    if is_two_column:
        # Place spanning words into whichever column their center is closer to, or header if near top
        for sw in spanning_words:
            center_x = (float(sw["x0"]) + float(sw["x1"])) / 2.0
            if center_x <= midpoint:
                left_words.append(sw)
            else:
                right_words.append(sw)

        lines: List[List[Dict[str, Any]]] = []
        lines.extend(_group_words_into_lines(header_words))
        lines.extend(_group_words_into_lines(left_words))
        lines.extend(_group_words_into_lines(right_words))
        return lines

    return _group_words_into_lines(words)


def _group_words_into_lines(words: List[Dict[str, Any]], y_tol: float = 4.5) -> List[List[Dict[str, Any]]]:
    """Group a list of words into top-to-bottom, left-to-right visual lines."""
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (round(float(w["top"]) / y_tol), float(w["x0"])))
    lines: List[List[Dict[str, Any]]] = []
    cur_line: List[Dict[str, Any]] = []
    cur_top: Optional[float] = None

    for w in sorted_words:
        top = float(w["top"])
        if cur_top is not None and abs(top - cur_top) > y_tol and cur_line:
            cur_line.sort(key=lambda item: float(item["x0"]))
            lines.append(cur_line)
            cur_line = [w]
            cur_top = top
        else:
            cur_line.append(w)
            if cur_top is None:
                cur_top = top

    if cur_line:
        cur_line.sort(key=lambda item: float(item["x0"]))
        lines.append(cur_line)

    return lines


def extract_bibliographic_metadata(
    pdf_path: Path,
    first_page_lines: List[List[Dict[str, Any]]],
    total_pages: int,
    paper_id_override: Optional[str] = None,
) -> PaperMetadata:
    """Extract paper title, authors, publication year, DOI, and abstract from PDF metadata & page 1."""
    pypdf_title = ""
    pypdf_author = ""
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        if reader.metadata:
            pypdf_title = (reader.metadata.title or "").strip()
            pypdf_author = (reader.metadata.author or "").strip()
    except Exception:
        pass

    line_strings = [
        clean_scientific_text(" ".join(w["text"] for w in line))
        for line in first_page_lines
    ]
    line_strings = [s for s in line_strings if s]

    # Title heuristic: prefer valid pypdf title, else first non-trivial line on page 1
    title = ""
    if pypdf_title and len(pypdf_title) > 5 and not pypdf_title.lower().endswith(".pdf"):
        title = pypdf_title
    else:
        for line_str in line_strings[:6]:
            cleaned_line = line_str.strip("[] ")
            if (
                len(cleaned_line) >= 8
                and not cleaned_line.lower().startswith(("arxiv:", "published as", "preprint"))
                and categorize_section_heading(cleaned_line) is None
            ):
                title = cleaned_line
                break
    if not title:
        title = pdf_path.stem.replace("_", " ").title()

    # Authors heuristic
    authors: List[str] = []
    if pypdf_author and len(pypdf_author) > 2:
        authors = [a.strip() for a in re.split(r"[,;]| and ", pypdf_author) if a.strip()]
    if not authors:
        for line_str in line_strings[1:6]:
            if line_str.lower().startswith("authors:"):
                raw_auth = line_str.split(":", 1)[1]
                raw_auth = re.sub(r"\(\d{4}\)", "", raw_auth)
                authors = [a.strip() for a in raw_auth.split(",") if a.strip()]
                break
    if not authors:
        authors = ["Unknown Author"]

    # Year & DOI heuristic from page 1 text
    page1_full = "\n".join(line_strings)
    year: Optional[int] = None
    year_matches = re.findall(r"\b(199\d|20[0-2]\d)\b", page1_full)
    if year_matches:
        year = int(year_matches[0])

    doi: Optional[str] = None
    doi_match = re.search(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b", page1_full)
    if doi_match:
        doi = doi_match.group(1)
    else:
        arxiv_match = re.search(r"arXiv:(\d{4}\.\d{4,5})", page1_full, flags=re.IGNORECASE)
        if arxiv_match:
            doi = f"10.48550/arXiv.{arxiv_match.group(1)}"

    # Abstract heuristic
    abstract = ""
    abs_match = re.search(
        r"(?:Abstract[:\s—\-]*)(.+?)(?:\n\s*(?:1\.?\s+Introduction|I\.?\s+Introduction)\b|\Z)",
        page1_full,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if abs_match:
        abstract = clean_scientific_text(abs_match.group(1))[:900]
    elif len(line_strings) > 2:
        abstract = clean_scientific_text(" ".join(line_strings[2:6]))[:600]

    # Deterministic or generated paper_id
    if paper_id_override:
        paper_id = paper_id_override
    else:
        stem_slug = re.sub(r"[^a-z0-9]+", "_", pdf_path.stem.lower()).strip("_")
        paper_id = f"paper_{stem_slug[:28]}" if stem_slug else f"paper_{uuid.uuid4().hex[:8]}"

    rel_filepath = file_store.get_relative_filepath(pdf_path)

    return PaperMetadata(
        id=paper_id,
        title=title,
        authors=authors[:10],
        year=year,
        abstract=abstract or None,
        doi=doi,
        filepath=rel_filepath,
        total_pages=max(1, total_pages),
    )


class HierarchicalPDFParser:
    """Parses scientific PDFs into section-labeled TextChunks with normalized bounding boxes."""

    def __init__(
        self,
        min_chunk_words: int = 12,
        target_chunk_words: int = 140,
        max_chunk_words: int = 210,
    ) -> None:
        self.min_chunk_words = min_chunk_words
        self.target_chunk_words = target_chunk_words
        self.max_chunk_words = max_chunk_words

    def parse_pdf(
        self,
        pdf_path: Path,
        paper_metadata_override: Optional[PaperMetadata] = None,
        paper_id_override: Optional[str] = None,
    ) -> Tuple[PaperMetadata, List[TextChunk]]:
        """Parse a PDF document and return (PaperMetadata, List[TextChunk])."""
        resolved_path = Path(pdf_path).resolve()
        if not resolved_path.exists():
            raise FileNotFoundError(f"PDF file not found: {resolved_path}")

        chunks: List[TextChunk] = []
        chunk_counter = 0
        current_section = "Abstract"

        with pdfplumber.open(str(resolved_path)) as pdf:
            total_pages = len(pdf.pages)
            if total_pages == 0:
                raise ValueError(f"PDF '{resolved_path.name}' contains 0 pages")

            first_page_words = pdf.pages[0].extract_words(
                x_tolerance=1.5,
                y_tolerance=3.0,
                keep_blank_chars=False,
            )
            first_page_lines = _detect_and_order_columns(
                first_page_words, float(pdf.pages[0].width or 612.0)
            )

            paper_meta = paper_metadata_override or extract_bibliographic_metadata(
                resolved_path,
                first_page_lines,
                total_pages=total_pages,
                paper_id_override=paper_id_override,
            )

            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1
                page_w = float(page.width or 612.0)
                page_h = float(page.height or 792.0)

                words = (
                    first_page_words
                    if page_idx == 0
                    else page.extract_words(
                        x_tolerance=1.5,
                        y_tolerance=3.0,
                        keep_blank_chars=False,
                    )
                )
                if not words:
                    continue

                lines = (
                    first_page_lines
                    if page_idx == 0
                    else _detect_and_order_columns(words, page_w)
                )

                current_block_words: List[Dict[str, Any]] = []
                current_word_count = 0
                prev_line_bottom: Optional[float] = None
                prev_line_x0: Optional[float] = None

                def _flush_chunk(block_words: List[Dict[str, Any]], sec_name: str) -> None:
                    nonlocal chunk_counter
                    if not block_words:
                        return
                    raw_str = " ".join(str(w["text"]) for w in block_words)
                    cleaned_str = clean_scientific_text(raw_str)
                    word_list = cleaned_str.split()
                    if len(word_list) < self.min_chunk_words:
                        return

                    x0 = max(0.0, min(float(w["x0"]) for w in block_words) / page_w)
                    y0 = max(0.0, min(float(w["top"]) for w in block_words) / page_h)
                    x1 = min(1.0, max(float(w["x1"]) for w in block_words) / page_w)
                    y1 = min(1.0, max(float(w["bottom"]) for w in block_words) / page_h)

                    width = max(0.05, min(1.0 - x0, x1 - x0))
                    height = max(0.02, min(1.0 - y0, y1 - y0))

                    chunks.append(
                        TextChunk(
                            id=f"{paper_meta.id}_c{chunk_counter}",
                            paper_id=paper_meta.id,
                            paper_title=paper_meta.title,
                            section=sec_name,
                            page_number=page_num,
                            bbox=BoundingBox(
                                page=page_num,
                                x=round(x0, 4),
                                y=round(y0, 4),
                                width=round(width, 4),
                                height=round(height, 4),
                            ),
                            text=cleaned_str,
                            token_count=max(1, len(word_list)),
                        )
                    )
                    chunk_counter += 1

                for line in lines:
                    line_raw = " ".join(str(w["text"]) for w in line).strip()
                    line_top = min(float(w["top"]) for w in line)
                    line_bottom = max(float(w["bottom"]) for w in line)
                    line_x0 = min(float(w["x0"]) for w in line)

                    detected_section = categorize_section_heading(line_raw)
                    if detected_section is not None:
                        _flush_chunk(current_block_words, current_section)
                        current_block_words = []
                        current_word_count = 0
                        current_section = detected_section
                        prev_line_bottom = line_bottom
                        prev_line_x0 = line_x0
                        continue

                    # Detect column switch (when x0 jumps from left column to right column and y jumps upward)
                    column_switched = (
                        prev_line_bottom is not None
                        and prev_line_x0 is not None
                        and (line_top < prev_line_bottom - 40.0)
                        and abs(line_x0 - prev_line_x0) > page_w * 0.25
                    )
                    vertical_gap = (
                        (line_top - prev_line_bottom) if prev_line_bottom is not None else 0.0
                    )

                    if (
                        column_switched
                        or (vertical_gap > 11.0 and current_word_count >= self.min_chunk_words)
                        or (current_word_count + len(line) > self.max_chunk_words)
                    ):
                        _flush_chunk(current_block_words, current_section)
                        current_block_words = list(line)
                        current_word_count = len(line)
                    else:
                        current_block_words.extend(line)
                        current_word_count += len(line)

                    prev_line_bottom = line_bottom
                    prev_line_x0 = line_x0

                _flush_chunk(current_block_words, current_section)

        return paper_meta, chunks


pdf_parser = HierarchicalPDFParser()

