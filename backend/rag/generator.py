"""Strict context-constrained synthesis generator with Gemini API & deterministic extractive fallback."""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple
import httpx

from backend.config import settings
from backend.models.paper import TextChunk
from backend.models.rag import CitationToken
from backend.rag.bm25_index import tokenize_scientific_text

def generate_clarifying_refusal(
    query: str,
    history: Optional[List[Any]] = None,
    ranked_candidates: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a helpful refusal explaining why context was insufficient and asking targeted follow-up questions."""
    from backend.storage.db import db

    papers = db.list_papers()
    p_titles = [p.title for p in papers[:4]]
    prior_citations: List[str] = []
    if history:
        for turn in reversed(history):
            if getattr(turn, "role", "") == "assistant" and getattr(turn, "paper_ids", None):
                prior_citations = list(turn.paper_ids)
                break

    q_lower = query.lower()
    needs_model_spec = any(w in q_lower for w in ["model", "models", "version", "variants", "equations", "formulas"])
    suggestions: List[str] = []

    if prior_citations:
        cited_papers = [p for p in papers if p.id in set(prior_citations)]
        cited_names = [p.title.split("(")[0].strip() for p in cited_papers[:3]]
        if needs_model_spec:
            suggestions.append(f"Could you specify if you are asking about the {len(cited_names)} models from the previous answer ({', '.join(cited_names)})?")
            suggestions.append("Give me just the governing equations for the 3 Cucker-Smale models")
        else:
            suggestions.append(f"Are you following up on the previously cited papers ({', '.join(cited_names)})?")
    else:
        if needs_model_spec:
            suggestions.append("Which model(s) are you referring to? (e.g. Cucker-Smale flocking models, Transformer attention architectures, or LoRA)")
            suggestions.append("What are the differences between the models in the 3 Cucker-Smale papers?")
        else:
            suggestions.append("Could you clarify the topic or name the specific paper or method you are interested in?")

    if p_titles and len(suggestions) < 3:
        suggestions.append(f"Compare the models discussed in '{p_titles[0]}'")

    explanation_lines = [
        "I couldn't find sufficient context in your uploaded papers to answer this specific query with certainty."
    ]
    if needs_model_spec:
        explanation_lines.append(
            "It looks like your question refers to specific models or versions, but doesn't specify which ones or which paper(s) to look in."
        )
    explanation_lines.append("\n**Suggested follow-ups / clarifications:**")
    for s in suggestions:
        explanation_lines.append(f"• *{s}*")

    return {
        "answer": "\n\n".join(explanation_lines),
        "status": "insufficient_context",
        "citations": [],
        "suggested_followups": suggestions,
        "model_used": "deterministic-guardrail",
    }

SYSTEM_GROUNDING_PROMPT = """You are ScholarGraph, a grounded scientific literature research assistant.
Rules:
1. Base every factual claim ONLY on the provided CONTEXT PASSAGES. Do NOT bring in outside facts about these papers, authors, or results.
2. You ARE expected to reason over the passages: compare, contrast, relate, and draw conclusions across papers,
   even when no single passage explicitly states the comparison. For example, if Paper A's equation uses
   a(t)(v_j(t) - v_i(t)) and Paper B's uses a(t - tau)(v_j(t - tau) - v_i(t)), you should explain that B introduces
   a time delay tau that A does not have. Such inferences are allowed as long as each underlying fact is cited.
3. When comparing models/methods, identify for each paper: the governing equations or mechanism, key assumptions
   (e.g., delays, communication weights, propagation speed), and main results/conditions (e.g., flocking conditions,
   asymptotic velocity). Then summarize the differences clearly (a markdown table is encouraged).
4. Every claim MUST include an inline citation token in the exact format [paper_id, Page X] for the passage(s) it relies on.
   Always use the full paper_id exactly as given (e.g. [paper_cuckersmale_with_delay, Page 2]); never write [Page X] alone,
   never use numbers like [1], and never combine sources in one bracket — write [paper_a, Page 1] [paper_b, Page 2] instead.
   Write math in LaTeX ($...$ inline, $$...$$ display). Never use raw HTML tags (such as <h4>, <strong>, <em>, <br>); write standard Markdown only (####, **, *, list bullets, markdown tables).
5. The passages were extracted from PDFs, so equations are often garbled: subscripts/superscripts are detached and
   placed after the symbol, summation limits and fraction parts appear on separate lines, and equation numbers like (1)
   are interleaved. Carefully RECONSTRUCT such equations into correct LaTeX from the surrounding symbols and text
   (e.g. "dv α N (2) i = a (t − τ)(v (t − τ) − v (t)), dt N ij j i j̸=i" is
   $\\frac{dv_i}{dt} = \\frac{\\alpha}{N}\\sum_{j\\neq i} a_{ij}(t-\\tau)\\,(v_j(t-\\tau) - v_i(t))$). Never claim a formula
   is missing if it is present in garbled form. Do not invent terms that are not supported by the garbled text.
6. When the user asks for formulas/equations, answer primarily with the reconstructed display equations for each
   paper/model (with a one-line description of each symbol and the equation's number in the paper if visible), not prose.
7. Use the CONVERSATION HISTORY only to understand what the user is referring to (e.g. "them", "the formulas", "each version");
   facts must still come from the CONTEXT PASSAGES.
8. Only if the passages are genuinely unrelated to the question, respond with the exact sentence:
"The ingested literature does not contain sufficient evidence to answer this query."
   If evidence is partial, answer what the passages support and briefly note what is not covered instead of refusing.
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


def _repair_bare_page_citations(text: str, valid_paper_ids: set) -> str:
    """Attach a paper_id to bare "[Page N]" tokens so every citation is clickable.

    - In markdown tables, the paper is taken from the column header (e.g. "Finite Speed [paper_paper1]").
    - Elsewhere, the most recent paper_id mentioned earlier in the same line/paragraph is used.
    """
    if "[Page" not in text and "[p." not in text:
        return text

    bare_re = re.compile(r"\[(?:Pages?|p\.?)\s*(\d+(?:\s*[-–,]\s*\d+)*)\]", re.IGNORECASE)
    pid_re = re.compile(r"(paper_[\w-]+)")
    lines = text.split("\n")
    header_cols: Optional[List[Optional[str]]] = None
    last_pid: Optional[str] = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            last_pid = None
            header_cols = None if not stripped.startswith("|") else header_cols
            continue

        if stripped.startswith("|"):
            cells = stripped.strip("|").split("|")
            if header_cols is None:
                header_cols = []
                for cell in cells:
                    m = pid_re.search(cell)
                    header_cols.append(m.group(1) if m and m.group(1) in valid_paper_ids else None)
                continue
            new_cells = []
            for col, cell in enumerate(cells):
                col_pid = header_cols[col] if col < len(header_cols) else None
                if col_pid:
                    cell = bare_re.sub(lambda m: f"[{col_pid}, Page {m.group(1)}]", cell)
                new_cells.append(cell)
            lines[i] = "|" + "|".join(new_cells) + "|"
            continue

        header_cols = None

        def _fix(m: "re.Match[str]", line_text: str = line) -> str:
            before = line_text[: m.start()]
            found = pid_re.findall(before)
            pid = next((p for p in reversed(found) if p in valid_paper_ids), None) or last_pid
            return f"[{pid}, Page {m.group(1)}]" if pid else m.group(0)

        lines[i] = bare_re.sub(_fix, line)
        found_line = [p for p in pid_re.findall(lines[i]) if p in valid_paper_ids]
        if found_line:
            last_pid = found_line[-1]

    return "\n".join(lines)


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
        with httpx.Client(timeout=60.0) as client:
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

    def quick_completion(self, prompt: str, api_key: str) -> str:
        """Fast, short, non-grounded completion used only for query rewriting. Returns '' on failure."""
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 120},
        }
        models = list(dict.fromkeys(["gemini-flash-lite-latest", settings.gemini_model]))
        try:
            with httpx.Client(timeout=8.0) as client:
                for model_name in models:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                    try:
                        resp = client.post(url, params={"key": api_key}, json=payload)
                    except Exception:
                        continue
                    if resp.status_code != 200:
                        continue
                    parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    text_out = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                    if text_out:
                        return text_out.splitlines()[0]
        except Exception:
            return ""
        return ""

    def generate(
        self,
        query: str,
        ranked_candidates: List[Dict[str, Any]],
        api_key_override: Optional[str] = None,
        prefer_extractive: bool = False,
        comparative: bool = False,
        formula_mode: bool = False,
        history: Optional[List[Any]] = None,
        retrieval_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a grounded answer and return status, answer, citations, and model_used."""
        guard_query = retrieval_query or query
        if not ranked_candidates or not _has_query_overlap(guard_query, ranked_candidates):
            return generate_clarifying_refusal(query, history=history, ranked_candidates=ranked_candidates)

        valid_candidates = [
            c
            for c in ranked_candidates
            if float(c.get("relevance_score", 0.0)) >= settings.min_relevance_threshold
        ]
        if not valid_candidates:
            return generate_clarifying_refusal(query, history=history, ranked_candidates=ranked_candidates)

        citations = build_citation_tokens(valid_candidates)
        if api_key_override and api_key_override.strip() == "LOCAL_FALLBACK":
            prefer_extractive = True
            effective_api_key = ""
        else:
            effective_api_key = (api_key_override or settings.gemini_api_key or "").strip()

        if effective_api_key and not prefer_extractive:
            # Group passages by paper so the model can contrast papers side by side
            by_paper: Dict[str, List[TextChunk]] = {}
            for cand in valid_candidates:
                c: TextChunk = cand["chunk"]
                by_paper.setdefault(c.paper_id, []).append(c)

            context_blocks: List[str] = []
            idx = 1
            for pid, p_chunks in by_paper.items():
                title = p_chunks[0].paper_title or pid
                block_lines = [f"=== PAPER paper_id={pid} | title={title} ==="]
                for c in sorted(p_chunks, key=lambda x: (x.page_number, x.id)):
                    block_lines.append(
                        f"PASSAGE {idx} | paper_id={c.paper_id} | Page={c.page_number} | Section={c.section}\n"
                        f"CONTENT: {c.text}"
                    )
                    idx += 1
                context_blocks.append("\n\n".join(block_lines))

            if formula_mode:
                instruction = (
                    "Output ONLY the governing equations of each paper's model: one short heading per paper, then "
                    "the reconstructed LaTeX display equations (including the definition of the interaction weights "
                    "a_ij and any delay term), each followed by its citation and a single compact line defining new "
                    "symbols. No introduction, no comparison table, no prose summary unless the user asked for it. "
                    "Cite [paper_id, Page X] for every equation:"
                )
            elif comparative or len(by_paper) > 1:
                instruction = (
                    "Compare the papers above: describe each paper's model/approach (include its key equations, "
                    "reconstructed in LaTeX), then explicitly list the differences (and similarities) you can infer "
                    "from the passages. Cite [paper_id, Page X] for every claim:"
                )
            else:
                instruction = "Provide a concise, grounded answer citing [paper_id, Page X] for every claim:"

            history_block = ""
            if history:
                lines = []
                for turn in history[-6:]:
                    content = (getattr(turn, "content", "") or "").strip()
                    if not content:
                        continue
                    role = getattr(turn, "role", "user").upper()
                    lines.append(f"{role}: {content[:700]}")
                if lines:
                    history_block = "CONVERSATION HISTORY (for reference resolution only):\n" + "\n".join(lines) + "\n\n"

            resolved = (
                f"\n(Interpreted in context as: {retrieval_query})"
                if retrieval_query and retrieval_query.strip() != query.strip()
                else ""
            )
            user_prompt = (
                history_block
                + f"CONTEXT PASSAGES ({len(by_paper)} papers):\n\n"
                + "\n\n".join(context_blocks)
                + f"\n\nUSER QUESTION: {query}{resolved}\n\n"
                + instruction
            )
            try:
                llm_text, used_model_name = self._call_gemini(user_prompt, effective_api_key)
                llm_lower = llm_text.lower()
                is_refusal = (
                    "insufficient evidence" in llm_lower
                    or "does not contain sufficient" in llm_lower
                    or "couldn't find relevant information" in llm_lower
                )
                if is_refusal:
                    clarification = generate_clarifying_refusal(query, history=history, ranked_candidates=valid_candidates)
                    clarification["model_used"] = used_model_name
                    # If Gemini provided a helpful partial explanation alongside the refusal, prepend it
                    if len(llm_text.strip()) > 100:
                        clarification["answer"] = f"{llm_text.strip()}\n\n---\n**Suggested follow-ups / clarifications:**\n" + "\n".join(f"• *{s}*" for s in clarification["suggested_followups"])
                    return clarification
                valid_paper_ids = {c.paper_id for c in citations}
                has_valid_citation = any(pid in llm_text for pid in valid_paper_ids)
                if llm_text and has_valid_citation:
                    llm_text = _repair_bare_page_citations(llm_text, valid_paper_ids)
                    # Only list sources the answer actually cites (paper_id + page), not every passage sent
                    cited_pairs = set()
                    for m in re.finditer(r"\[([^\]]+)\]", llm_text):
                        for part in m.group(1).split(";"):
                            pm = re.match(r"\s*(paper_[\w-]+)\s*,\s*(?:Pages?|p\.?)\s*([\d\s,\-–]+)", part, re.I)
                            if not pm:
                                continue
                            nums = [int(n) for n in re.findall(r"\d+", pm.group(2))]
                            if len(nums) == 2 and re.search(r"[-–]", pm.group(2)):
                                nums = list(range(nums[0], nums[1] + 1))
                            for n in nums:
                                cited_pairs.add((pm.group(1), n))
                    used = [c for c in citations if (c.paper_id, c.page) in cited_pairs]
                    return {
                        "answer": llm_text,
                        "status": "success",
                        "citations": used or citations,
                        "model_used": used_model_name,
                    }
            except Exception:
                pass

        extractive_answer = extractive_fallback_synthesis(query, valid_candidates)
        if "insufficient evidence" in extractive_answer.lower() or len(extractive_answer.strip()) < 30:
            return generate_clarifying_refusal(query, history=history, ranked_candidates=valid_candidates)

        return {
            "answer": extractive_answer,
            "status": "success",
            "citations": citations,
            "model_used": "extractive-fallback",
        }


generator = GroundedGenerator()
