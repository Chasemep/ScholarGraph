"""Centralized prompt templates, instruction configurations, and refusal formatting for ScholarGraph."""

from typing import Any, Dict, List, Optional

REFUSAL_MESSAGE = "The ingested literature does not contain sufficient evidence to answer this query."

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
   are interleaved. Carefully RECONSTRUCT such equations into correct LaTeX from the surrounding symbols and text.
6. When the user asks for formulas/equations, answer primarily with the reconstructed display equations for each
   paper/model (with a one-line description of each symbol and the equation's number in the paper if visible), not prose.
7. Use the CONVERSATION HISTORY only to understand what the user is referring to (e.g. "them", "the formulas", "each version");
   facts must still come from the CONTEXT PASSAGES.
8. Only if the passages are genuinely unrelated to the question, respond with the exact sentence:
"The ingested literature does not contain sufficient evidence to answer this query."
   If evidence is partial, answer what the passages support and briefly note what is not covered instead of refusing.
"""

COMPARATIVE_PROMPT_EXTENSION = """
Provide a structured cross-paper analysis:
- Present each method's primary architecture/mechanism.
- Contrast their key mathematical assumptions and design tradeoffs.
- Provide a clear Markdown comparison table summarizing differences.
"""

FORMULA_PROMPT_EXTENSION = """
Reconstruct the complete mathematical equations from the passages:
- Use LaTeX display equations ($$ ... $$) for all primary governing equations.
- Define each symbol and parameter immediately beneath the equation.
- Attribute each formula to its specific paper and page citation token.
"""


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
            suggestions.append("Give me just the governing equations for the models")
        else:
            suggestions.append(f"Are you following up on the previously cited papers ({', '.join(cited_names)})?")
    else:
        if needs_model_spec:
            suggestions.append("Which model(s) are you referring to?")
            suggestions.append("What are the differences between the models in your uploaded papers?")
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

