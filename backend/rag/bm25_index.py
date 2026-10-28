"""Sparse lexical keyword index using rank_bm25.BM25Okapi with scientific tokenization."""

import re
from typing import Any, Dict, List, Optional
from rank_bm25 import BM25Okapi

from backend.models.paper import TextChunk

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "is", "it", "its", "of", "on", "or", "that",
    "the", "their", "there", "these", "this", "to", "was", "were",
    "which", "will", "with", "we", "our", "can", "into", "such",
    # Conversational / prompt meta-words that should not dilute scientific keyword matching
    "explain", "compare", "comparison", "describe", "summarize", "corpus",
    "paper", "papers", "propose", "proposes", "adapt", "adapts", "evaluate",
    "evaluates", "how", "what", "why", "where", "when", "does", "do", "did",
    "each", "both", "all", "versus", "vs", "between", "across", "used", "using",
}


def tokenize_scientific_text(text: str) -> List[str]:
    """Tokenize scientific text preserving hyphenated terms, alphanumeric symbols, and acronyms."""
    if not text:
        return []
    normalized = re.sub(r"(\d),(\d)", r"\1\2", text.lower())
    raw_tokens = re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", normalized)
    return [tok for tok in raw_tokens if tok not in STOPWORDS and len(tok) > 1]


class BM25IndexManager:
    """In-memory BM25Okapi lexical index synchronized with SQLite paper chunks."""

    def __init__(self) -> None:
        self.chunks: List[TextChunk] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None

    def build_index(self, chunks: List[TextChunk]) -> int:
        """Build or rebuild the BM25 index over the provided list of TextChunk objects."""
        self.chunks = list(chunks)
        if not self.chunks:
            self.tokenized_corpus = []
            self.bm25 = None
            return 0

        self.tokenized_corpus = [
            tokenize_scientific_text(f"{c.paper_title or ''} {c.section} {c.text}")
            for c in self.chunks
        ]
        if any(len(tokens) > 0 for tokens in self.tokenized_corpus):
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None
        return len(self.chunks)

    def search(
        self,
        query: str,
        top_k: int = 20,
        paper_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve top-K chunks ranked by BM25 lexical relevance score."""
        if not self.bm25 or not self.chunks or not query or not query.strip():
            return []

        query_tokens = tokenize_scientific_text(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)
        allowed_papers = set(paper_ids) if paper_ids else None

        scored_indices: List[tuple[int, float]] = []
        for idx, score in enumerate(scores):
            if score <= 0.0:
                continue
            chunk = self.chunks[idx]
            if allowed_papers is not None and chunk.paper_id not in allowed_papers:
                continue
            scored_indices.append((idx, float(score)))

        scored_indices.sort(key=lambda item: item[1], reverse=True)
        top_items = scored_indices[:top_k]

        return [
            {
                "chunk": self.chunks[idx],
                "score": score,
                "rank": rank_idx + 1,
            }
            for rank_idx, (idx, score) in enumerate(top_items)
        ]


bm25_index = BM25IndexManager()
