"""Strict context-constrained synthesis generator with Gemini API & deterministic extractive fallback."""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple
import httpx

from backend.config import settings
from backend.models.paper import TextChunk
from backend.models.rag import CitationToken
from backend.rag.bm25_index import tokenize_scientific_text

REFUSAL_MESSAGE = "The ingested literature does not contain sufficient evidence to answer this query."

SYSTEM_GROUNDING_PROMPT = """You are ScholarGraph, a strictly grounded scientific literature research assistant.
You MUST obey the Zero-Hallucination Invariant:
1. Answer the user's question ONLY using facts explicitly stated in the provided CONTEXT PASSAGES below.
2. Do NOT use external pre-trained knowledge, assumptions, or extrapolations.
3. Every factual claim or sentence MUST include an inline citation token in the exact format [paper_id, Page X] corresponding to the passage where the fact appears.
4. If the provided CONTEXT PASSAGES do not contain sufficient evidence to answer the question, respond with the exact sentence:
"The ingested literature does not contain sufficient evidence to answer this query."
"""


def _has_query_overlap(query: str, ranked_candidates: List[Dict[str, Any]]) -> bool:
    """Verify whether the top retrieved candidates share meaningful domain overlap with the query."""
    if not ranked_candidates:
        return False

    query_tokens = set(tokenize_scientific_text(query))
    if not query_tokens:
        return False

    for cand in ranked_candidates[:3]:
        chunk: TextChunk = cand["chunk"]
        chunk_tokens = set(
            tokenize_scientific_text(f"{chunk.paper_title or ''} {chunk.section} {chunk.text}")
        )
        overlap = query_tokens.intersection(chunk_tokens)
        if len(overlap) >= 1 and cand.get("relevance_score", 0.0) >= settings.min_relevance_threshold:
            return True

    top_score = float(ranked_candidates[0].get("relevance_score", 0.0))
    return top_score >= (settings.min_relevance_threshold + 0.35)


def build_citation_tokens(ranked_candidates: List[Dict[str, Any]]) -> List[CitationToken]:
    """Convert ranked candidate dicts into validated CitationToken objects."""
    citations: List[CitationToken] = []
    for cand in ranked_candidates:
        chunk: TextChunk = cand["chunk"]
        score = float(cand.get("relevance_score", 0.0))
        snippet = chunk.text[:240].strip() + ("..." if len(chunk.text) > 240 else "")
        citations.append(
            CitationToken(
                paper_id=chunk.paper_id,
                paper_title=chunk.paper_title or chunk.paper_id,
                page=chunk.page_number,
                bbox=chunk.bbox,
                chunk_id=chunk.id,
                section=chunk.section,
                snippet=snippet,
                relevance_score=round(max(0.0, min(1.0, score)), 4),
            )
        )
    return citations


def extractive_fallback_synthesis(
    query: str,
    ranked_candidates: List[Dict[str, Any]],
) -> str:
    """Deterministic, 100% grounded extractive synthesis when LLM API is unavailable or disabled."""
    query_tokens = set(tokenize_scientific_text(query))
    synthesized_sentences: List[str] = []
    seen_sentences: set[str] = set()

    for cand in ranked_candidates:
        chunk: TextChunk = cand["chunk"]
        raw_sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", chunk.text.strip())
            if len(s.strip()) > 20
        ]
        if not raw_sentences:
            raw_sentences = [chunk.text.strip()]

        scored_sents: List[Tuple[int, str]] = []
        for s in raw_sentences:
            s_tokens = set(tokenize_scientific_text(s))
            overlap_count = len(query_tokens.intersection(s_tokens))
            scored_sents.append((overlap_count, s))

        scored_sents.sort(key=lambda x: x[0], reverse=True)
        best_sent = scored_sents[0][1].rstrip(".")
        norm_key = best_sent.lower()
        if norm_key in seen_sentences:
            continue
        seen_sentences.add(norm_key)

        citation_badge = f"[{chunk.paper_id}, Page {chunk.page_number}]"
        synthesized_sentences.append(f"{best_sent} {citation_badge}.")
        if len(synthesized_sentences) >= 4:
            break

    if not synthesized_sentences:
        return REFUSAL_MESSAGE

    return " ".join(synthesized_sentences)


class GroundedGenerator:
    """Executes strictly grounded answer synthesis with zero-hallucination guardrails."""

    def __init__(
        self,
        llm_callable: Optional[Callable[[str, str, str], str]] = None,
    ) -> None:
        self._llm_callable = llm_callable

    def _call_gemini(self, prompt: str, api_key: str) -> Tuple[str, str]:
        """Invoke Google Gemini REST API with temperature=0.0 for deterministic grounded generation."""
        if self._llm_callable is not None:
            return self._llm_callable(SYSTEM_GROUNDING_PROMPT, prompt, api_key), settings.gemini_model

        candidate_models = [
            settings.gemini_model,
            "gemini-3-flash-preview",
            "gemini-flash-lite-latest",
        ]
        seen: set[str] = set()
        models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]

        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_GROUNDING_PROMPT}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 4096,
            },
        }

        last_err: Optional[Exception] = None
        with httpx.Client(timeout=20.0) as client:
            for model_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                try:
                    resp = client.post(url, params={"key": api_key}, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        parts = (
                            data.get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [])
                        )
                        text_chunks = [p.get("text", "") for p in parts if "text" in p]
                        text_out = "".join(text_chunks).strip()
                        if text_out:
                            return text_out, model_name
                except Exception as exc:
                    last_err = exc
                    continue

        if last_err:
            raise last_err
        raise RuntimeError("All Gemini model endpoints failed or returned empty responses.")

    def generate(
        self,
        query: str,
        ranked_candidates: List[Dict[str, Any]],
        api_key_override: Optional[str] = None,
        prefer_extractive: bool = False,
    ) -> Dict[str, Any]:
        """Generate a grounded answer and return status, answer, citations, and model_used."""
        if not ranked_candidates or not _has_query_overlap(query, ranked_candidates):
            return {
                "answer": REFUSAL_MESSAGE,
                "status": "insufficient_context",
                "citations": [],
                "model_used": "deterministic-guardrail",
            }

        valid_candidates = [
            c
            for c in ranked_candidates
            if float(c.get("relevance_score", 0.0)) >= settings.min_relevance_threshold
        ]
        if not valid_candidates:
            return {
                "answer": REFUSAL_MESSAGE,
                "status": "insufficient_context",
                "citations": [],
                "model_used": "deterministic-guardrail",
            }

        citations = build_citation_tokens(valid_candidates)
        effective_api_key = (api_key_override or settings.gemini_api_key or "").strip()

        if effective_api_key and not prefer_extractive:
            context_blocks: List[str] = []
            for idx, cand in enumerate(valid_candidates, start=1):
                c: TextChunk = cand["chunk"]
                context_blocks.append(
                    f"PASSAGE {idx} | paper_id={c.paper_id} | title={c.paper_title or c.paper_id} "
                    f"| Page={c.page_number} | Section={c.section}\n"
                    f"CONTENT: {c.text}"
                )
            user_prompt = (
                f"CONTEXT PASSAGES:\n\n"
                + "\n\n".join(context_blocks)
                + f"\n\nUSER QUESTION: {query}\n\n"
                "Provide a concise, strictly grounded synthesis citing [paper_id, Page X] for every claim:"
            )
            try:
                llm_text, used_model_name = self._call_gemini(user_prompt, effective_api_key)
                if REFUSAL_MESSAGE.lower() in llm_text.lower():
                    return {
                        "answer": REFUSAL_MESSAGE,
                        "status": "insufficient_context",
                        "citations": [],
                        "model_used": used_model_name,
                    }
                valid_paper_ids = {c.paper_id for c in citations}
                has_valid_citation = any(pid in llm_text for pid in valid_paper_ids)
                if llm_text and has_valid_citation:
                    return {
                        "answer": llm_text,
                        "status": "success",
                        "citations": citations,
                        "model_used": used_model_name,
                    }
            except Exception:
                pass

        extractive_answer = extractive_fallback_synthesis(query, valid_candidates)
        if extractive_answer == REFUSAL_MESSAGE:
            return {
                "answer": REFUSAL_MESSAGE,
                "status": "insufficient_context",
                "citations": [],
                "model_used": "deterministic-guardrail",
            }

        return {
            "answer": extractive_answer,
            "status": "success",
            "citations": citations,
            "model_used": "extractive-fallback",
        }


generator = GroundedGenerator()
