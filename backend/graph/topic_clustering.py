"""Automatic hierarchical topic and citation clustering for academic paper collections.

Groups any set of uploaded papers into:
1. Top-level Macro-Categories (Groups) based on combined content similarity, shared
   methods/datasets, and citation structure.
2. Optional nested Subcategories (Subgroups) when a Macro-Category contains multiple
   papers covering distinct sub-topics or model variants.
"""

from collections import Counter
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

from backend.models.paper import PaperMetadata, TextChunk
from backend.rag.bm25_index import tokenize_scientific_text

# Generic academic words excluded when naming topic clusters or computing discriminative phrases
ACADEMIC_STOPWORDS: Set[str] = {
    "paper",
    "papers",
    "study",
    "studies",
    "method",
    "methods",
    "approach",
    "approaches",
    "model",
    "models",
    "system",
    "systems",
    "result",
    "results",
    "section",
    "sections",
    "figure",
    "figures",
    "table",
    "tables",
    "propose",
    "proposed",
    "introduce",
    "introduced",
    "present",
    "presented",
    "show",
    "shown",
    "demonstrate",
    "using",
    "used",
    "based",
    "new",
    "novel",
    "fast",
    "efficient",
    "effective",
    "large",
    "small",
    "high",
    "low",
    "state",
    "art",
    "work",
    "works",
    "problem",
    "problems",
    "task",
    "tasks",
    "performance",
    "experiments",
    "experimental",
    "evaluation",
    "analysis",
    "framework",
    "algorithm",
    "algorithms",
    "architecture",
    "architectures",
    "pre",
    "post",
    "non",
    "via",
    "towards",
    "beyond",
    "all",
    "need",
    "you",
    "our",
    "their",
    "these",
    "those",
    "such",
    "also",
    "can",
    "may",
    "well",
    "First",
    "first",
    "second",
    "two",
    "three",
    "one",
    "et",
    "al",
    "ieee",
    "acm",
    "arxiv",
    "preprint",
    "proceedings",
    "conference",
    "journal",
    "transactions",
    "university",
    "department",
    "institute",
    "research",
    "science",
    "sciences",
    "mathematics",
    "mathematical",
}


def _clean_paper_title(raw_title: str) -> str:
    """Remove trailing (Author, Year) suffixes and normalize whitespace."""
    cleaned = re.sub(r"\s*\([^)]*\d{4}[^)]*\)\s*$", "", raw_title or "").strip()
    return cleaned or raw_title


def _sanitize_concept_phrase(raw: str) -> Optional[str]:
    """Clean extracted method/concept strings and reject noisy section-header artifacts."""
    if not raw:
        return None
    s = re.sub(r"\s+", " ", raw).strip(" .,;:!?()[]{}\"'")
    # Strip leading articles
    s = re.sub(r"^(?:the|an|a)\s+", "", s, flags=re.IGNORECASE).strip()
    if len(s) < 3 or len(s) > 42:
        return None
    words = s.split()
    # Reject strings containing 2+ consecutive ALL-CAPS words longer than 2 chars that look like section headers
    all_caps_words = [
        w for w in words if w.isupper() and len(w) > 2 and w not in {"BERT", "GPT", "LORA", "ROPE", "GLUE", "BLEU", "CUDA", "SRAM", "HBM", "FFN", "RNN", "CNN", "LSTM", "MLP", "NLP", "LLM", "LLMS"}
    ]
    if len(all_caps_words) >= 2:
        return None
    if all(w.lower() in ACADEMIC_STOPWORDS for w in words):
        return None
    return s


def _extract_candidate_phrases(
    paper: PaperMetadata,
    chunks: List[TextChunk],
    mined_entities: Dict[str, Any],
) -> List[Tuple[str, float]]:
    """Extract weighted domain keyphrases from a paper's title, methods, datasets, and abstract."""
    phrases: Counter[str] = Counter()

    # 1. Extracted canonical or custom methods carry strong topical signal
    seen_methods: Set[str] = set()
    for raw_method in mined_entities.get("methods", []):
        method = _sanitize_concept_phrase(raw_method)
        if not method or method.lower() in seen_methods:
            continue
        seen_methods.add(method.lower())
        phrases[method] += 6.0

    # 2. Title phrases (before and after colon)
    clean_title = _clean_paper_title(paper.title)
    parts = [p.strip() for p in re.split(r"[:—–]", clean_title) if p.strip()]
    for idx, part in enumerate(parts):
        weight = 5.5 if idx == 0 else 4.2
        words = [
            w.strip(".,;!?()[]{}\"'")
            for w in part.split()
            if len(w.strip(".,;!?()[]{}\"'")) >= 2
        ]
        content_words = [
            w for w in words if w.lower() not in ACADEMIC_STOPWORDS and not w.isdigit()
        ]
        if 1 <= len(content_words) <= 4:
            phrase = _sanitize_concept_phrase(" ".join(content_words))
            if phrase and len(phrase) >= 4:
                phrases[_smart_title_case(phrase)] += weight

        # Also add bigrams and trigrams from longer title clauses
        for n in (3, 2):
            for i in range(len(words) - n + 1):
                gram = words[i : i + n]
                if (
                    gram[0].lower() in ACADEMIC_STOPWORDS
                    or gram[-1].lower() in ACADEMIC_STOPWORDS
                ):
                    continue
                meaningful = [w for w in gram if w.lower() not in ACADEMIC_STOPWORDS]
                if len(meaningful) >= 1:
                    candidate = _sanitize_concept_phrase(_smart_title_case(" ".join(gram)))
                    if candidate and len(candidate) >= 5:
                        phrases[candidate] += 3.2

    # 3. Abstract / opening chunk capitalized multi-word technical concepts & domain themes
    intro_text = f"{clean_title} {paper.abstract or ''} " + " ".join(c.text for c in chunks[:2])
    intro_sample = intro_text[:3500]
    tech_matches = re.findall(
        r"\b([A-Z][a-zA-Z0-9-]+(?:\s+[A-Z][a-zA-Z0-9-]+){1,3})\b",
        intro_sample,
    )
    for tm in tech_matches:
        clean_tm = _sanitize_concept_phrase(tm)
        if not clean_tm:
            continue
        tm_words = clean_tm.split()
        if any(w.lower() in ACADEMIC_STOPWORDS for w in tm_words):
            continue
        if 6 <= len(clean_tm) <= 38:
            phrases[clean_tm] += 1.5

    # Detect recurring broad academic themes from title + abstract so macro-categories get natural umbrella names
    theme_patterns = [
        (r"\btransformers?\b", "Transformers"),
        (r"\bself[- ]attention\b", "Self-Attention"),
        (r"\blanguage\s+models?\b", "Language Models"),
        (r"\bpre-?train(?:ing|ed)\b", "Pre-training"),
        (r"\bfine-?tun(?:ing|ed)\b|\badaptation\b", "Model Adaptation"),
        (r"\bposition(?:al)?\s+(?:encoding|embedding)s?\b", "Positional Encoding"),
        (r"\bflocking\b", "Flocking Dynamics"),
        (r"\bconsensus\b", "Consensus Emergence"),
        (r"\bgraph\s+neural\s+networks?\b", "Graph Neural Networks"),
        (r"\bdiffusion\s+models?\b", "Diffusion Models"),
        (r"\breinforcement\s+learning\b", "Reinforcement Learning"),
    ]
    for pat, label in theme_patterns:
        if re.search(pat, intro_sample, flags=re.IGNORECASE):
            phrases[label] += 4.5

    return phrases.most_common(24)


def _smart_title_case(phrase: str) -> str:
    """Title-case a phrase while preserving existing acronyms like LoRA, BERT, RoPE, GPU, HBM."""
    small_words = {"of", "in", "on", "for", "and", "to", "with", "by", "at", "from"}
    words = phrase.split()
    out: List[str] = []
    for i, w in enumerate(words):
        if any(ch.isupper() for ch in w[1:]) or w.isupper():
            out.append(w)
        elif i > 0 and w.lower() in small_words:
            out.append(w.lower())
        else:
            out.append(w.capitalize())
    return " ".join(out)


def _build_paper_tfidf_vectors(
    papers: List[PaperMetadata],
    chunks_by_paper: Dict[str, List[TextChunk]],
    mined_by_paper: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, float]]:
    """Build L2-normalized TF-IDF content vectors for each paper."""
    raw_term_counts: Dict[str, Counter[str]] = {}
    doc_freq: Counter[str] = Counter()
    n_docs = max(1, len(papers))

    for paper in papers:
        p_chunks = chunks_by_paper.get(paper.id, [])
        mined = mined_by_paper.get(paper.id, {})
        title_text = (_clean_paper_title(paper.title) + " ") * 4
        methods_text = (" ".join(mined.get("methods", [])) + " ") * 4
        datasets_text = (" ".join(mined.get("datasets", [])) + " ") * 2
        abstract_text = ((paper.abstract or "") + " ") * 2
        body_sample = " ".join(c.text for c in p_chunks[:5])

        combined = f"{title_text} {methods_text} {datasets_text} {abstract_text} {body_sample}"
        tokens = [
            t
            for t in tokenize_scientific_text(combined)
            if t not in ACADEMIC_STOPWORDS and len(t) >= 3 and not t.isdigit()
        ]
        counts = Counter(tokens)
        raw_term_counts[paper.id] = counts
        for term in counts.keys():
            doc_freq[term] += 1

    tfidf_vectors: Dict[str, Dict[str, float]] = {}
    for paper in papers:
        counts = raw_term_counts[paper.id]
        vec: Dict[str, float] = {}
        norm_sq = 0.0
        for term, tf in counts.items():
            df = doc_freq[term]
            # Smooth IDF so shared domain terms still contribute while specific terms weigh more
            idf = math.log((1.0 + n_docs) / (1.0 + df)) + 1.0
            val = (1.0 + math.log(tf)) * idf
            vec[term] = val
            norm_sq += val * val
        norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
        tfidf_vectors[paper.id] = {k: v / norm for k, v in vec.items()}

    return tfidf_vectors


def _cosine_sim(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) > len(vec_b):
        vec_a, vec_b = vec_b, vec_a
    dot = sum(val * vec_b.get(term, 0.0) for term, val in vec_a.items())
    return max(0.0, min(1.0, dot))


def _agglomerative_cluster(
    paper_ids: List[str],
    affinity_matrix: Dict[Tuple[str, str], float],
    threshold: float,
) -> List[List[str]]:
    """Deterministic average-linkage agglomerative clustering over an affinity matrix."""
    clusters: List[List[str]] = [[pid] for pid in paper_ids]

    while len(clusters) > 1:
        best_score = -1.0
        best_pair: Optional[Tuple[int, int]] = None

        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                c_i = clusters[i]
                c_j = clusters[j]
                total_sim = 0.0
                count = 0
                for u in c_i:
                    for v in c_j:
                        key = (u, v) if u < v else (v, u)
                        total_sim += affinity_matrix.get(key, 0.0)
                        count += 1
                avg_sim = total_sim / max(1, count)
                if avg_sim > best_score:
                    best_score = avg_sim
                    best_pair = (i, j)

        if best_pair is None or best_score < threshold:
            break

        i, j = best_pair
        merged = clusters[i] + clusters[j]
        clusters = [
            c for idx, c in enumerate(clusters) if idx not in (i, j)
        ] + [merged]

    return clusters


def _choose_cluster_label(
    cluster_pids: List[str],
    all_cluster_pids: List[List[str]],
    papers_by_id: Dict[str, PaperMetadata],
    phrases_by_paper: Dict[str, List[Tuple[str, float]]],
    mined_by_paper: Dict[str, Dict[str, Any]],
    is_subgroup: bool = False,
    parent_label: str = "",
) -> str:
    """Generate a concise, accurate human-readable category/subcategory title for a cluster."""
    parent_tokens = {
        w.lower().strip(".,;:!?()[]{}")
        for w in re.split(r"[\s&/,-]+", parent_label)
        if len(w.strip(".,;:!?()[]{}")) >= 3
    }

    if len(cluster_pids) == 1:
        single_paper = papers_by_id[cluster_pids[0]]
        single_mined = mined_by_paper.get(single_paper.id, {})
        clean_t = _clean_paper_title(single_paper.title)

        # Clean candidate methods
        methods = [
            m
            for raw_m in single_mined.get("methods", [])
            for m in [_sanitize_concept_phrase(raw_m)]
            if m is not None
        ]

        if ":" in clean_t:
            prefix, suffix = [p.strip() for p in clean_t.split(":", 1)]
            # Look for a canonical method that explicitly ends with (prefix), e.g., Low-Rank Adaptation (LoRA)
            for m in methods:
                if f"({prefix.lower()})" in m.lower() and m.lower() not in parent_label.lower():
                    return m
            if 3 <= len(prefix) <= 34 and prefix.lower() not in parent_label.lower():
                if len(prefix) <= 10 and suffix:
                    suffix_words = [
                        w
                        for w in suffix.split()
                        if w.lower() not in ACADEMIC_STOPWORDS
                    ][:3]
                    if suffix_words:
                        combined = f"{prefix}: {_smart_title_case(' '.join(suffix_words))}"
                        if len(combined) <= 38:
                            return combined
                return _smart_title_case(prefix)

        if methods:
            for m in methods:
                if m.lower() not in parent_label.lower():
                    return m
            return methods[0]

        words = [
            w for w in clean_t.split() if w.lower() not in ACADEMIC_STOPWORDS
        ]
        if words:
            return _smart_title_case(" ".join(words[:4]))
        return clean_t[:36]

    # Multi-paper cluster: score candidate phrases by cluster coverage and discriminativeness
    phrase_scores: Counter[str] = Counter()
    phrase_doc_coverage: Counter[str] = Counter()
    canonical_display: Dict[str, str] = {}

    other_pids = {
        pid
        for c in all_cluster_pids
        if set(c) != set(cluster_pids)
        for pid in c
    }
    other_phrases: Set[str] = set()
    for opid in other_pids:
        for ph, _ in phrases_by_paper.get(opid, []):
            other_phrases.add(ph.lower())

    for pid in cluster_pids:
        seen_in_doc: Set[str] = set()
        for ph, weight in phrases_by_paper.get(pid, []):
            ph_clean = _sanitize_concept_phrase(ph)
            if not ph_clean:
                continue
            ph_key = ph_clean.lower()
            if is_subgroup and parent_label:
                if ph_key in parent_label.lower():
                    continue
                ph_tokens = {w.lower() for w in re.split(r"[\s&/,-]+", ph_clean) if len(w) >= 3}
                if ph_tokens and ph_tokens.issubset(parent_tokens):
                    continue
            if ph_key not in canonical_display:
                canonical_display[ph_key] = ph_clean
            phrase_scores[ph_key] += weight
            if ph_key not in seen_in_doc:
                phrase_doc_coverage[ph_key] += 1
                seen_in_doc.add(ph_key)

    best_phrases: List[Tuple[float, str]] = []
    cluster_size = len(cluster_pids)
    for ph_key, base_score in phrase_scores.items():
        cov = phrase_doc_coverage[ph_key]
        # Strongly reward concepts shared by a majority of papers in the cluster
        coverage_multiplier = (1.0 + 1.4 * (cov - 1)) * (1.35 if cov >= max(2, math.ceil(cluster_size * 0.6)) else 1.0)
        discriminative_bonus = 1.4 if ph_key not in other_phrases else 0.85
        final_score = base_score * coverage_multiplier * discriminative_bonus
        best_phrases.append((final_score, canonical_display[ph_key]))

    best_phrases.sort(key=lambda x: x[0], reverse=True)

    if not best_phrases:
        first_title = _clean_paper_title(papers_by_id[cluster_pids[0]].title)
        return first_title[:34]

    top1 = best_phrases[0][1]
    # Combine top 2 complementary themes if concise
    if len(best_phrases) >= 2:
        for _, candidate2 in best_phrases[1:5]:
            t1_tokens = {w.lower().rstrip("s") for w in re.split(r"[\s&/,-]+", top1) if len(w) >= 3}
            t2_tokens = {w.lower().rstrip("s") for w in re.split(r"[\s&/,-]+", candidate2) if len(w) >= 3}
            if not t1_tokens.intersection(t2_tokens) and len(top1) + len(candidate2) <= 38:
                return f"{top1} & {candidate2}"

    return top1


def _extract_grounded_paper_excerpt(
    paper: PaperMetadata,
    p_chunks: List[TextChunk],
) -> Dict[str, Any]:
    """Extract a clean, strictly paper-sourced summary excerpt and PDF location from a paper's abstract/opening chunk."""
    first_chunk = p_chunks[0] if p_chunks else None
    raw_text = (paper.abstract or "").strip()
    if len(raw_text) < 40 and first_chunk:
        raw_text = (first_chunk.text or "").strip()

    # Clean leading boilerplate or classification lines while keeping only text from the paper itself
    cleaned = re.sub(r"^\s*(?:abstract|summary)\s*[:.—-]?\s*", "", raw_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*[.,;:-]+\s*", "", cleaned)
    # Remove MSC / Keywords lines if embedded in opening chunk
    lines = [
        ln.strip()
        for ln in cleaned.splitlines()
        if ln.strip()
        and not ln.strip().lower().startswith("keywords and phrases:")
        and not ln.strip().lower().startswith("mathematics subject classification")
    ]
    joined = re.sub(r"\s+", " ", " ".join(lines)).strip()

    # Split into sentences and take up to the first 3 sentences (<= 420 chars) from the paper
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", joined) if len(s.strip()) >= 20]
    selected: List[str] = []
    total_len = 0
    for s in sentences:
        if total_len + len(s) > 420 and selected:
            break
        selected.append(s)
        total_len += len(s)
        if len(selected) >= 3:
            break

    excerpt = " ".join(selected) if selected else joined[:380]

    bbox_dict = None
    if first_chunk and getattr(first_chunk, "bbox", None):
        bb = first_chunk.bbox
        bbox_dict = bb.model_dump() if hasattr(bb, "model_dump") else {
            "page": bb.page,
            "x": bb.x,
            "y": bb.y,
            "width": bb.width,
            "height": bb.height,
        }

    return {
        "paper_id": paper.id,
        "paper_title": _clean_paper_title(paper.title),
        "year": paper.year,
        "authors": paper.authors or [],
        "excerpt": excerpt,
        "chunk_id": first_chunk.id if first_chunk else f"{paper.id}_c0",
        "page": first_chunk.page_number if first_chunk else 1,
        "section": (getattr(first_chunk, "section", None) or "Abstract / Introduction") if first_chunk else "Abstract",
        "bbox": bbox_dict,
    }


def _build_cluster_topic_summary(
    cluster_pids: List[str],
    papers_by_id: Dict[str, PaperMetadata],
    chunks_by_paper: Dict[str, List[TextChunk]],
    mined_by_paper: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a strictly paper-grounded topic explanation and chronological paper breakdown for a Category or Subcategory."""
    sorted_pids = sorted(
        cluster_pids,
        key=lambda pid: (papers_by_id[pid].year or 9999, papers_by_id[pid].title or ""),
    )

    paper_excerpts: List[Dict[str, Any]] = []
    overview_parts: List[str] = []
    methods_counter: Counter[str] = Counter()
    datasets_counter: Counter[str] = Counter()

    for pid in sorted_pids:
        paper = papers_by_id[pid]
        p_chunks = chunks_by_paper.get(pid, [])
        mined = mined_by_paper.get(pid, {})

        ex_info = _extract_grounded_paper_excerpt(paper, p_chunks)
        clean_methods = [
            m
            for raw_m in mined.get("methods", [])
            for m in [_sanitize_concept_phrase(raw_m)]
            if m is not None
        ]
        clean_datasets = list(dict.fromkeys(mined.get("datasets", [])))

        ex_info["methods"] = clean_methods[:5]
        ex_info["datasets"] = clean_datasets[:4]
        paper_excerpts.append(ex_info)

        for m in clean_methods:
            methods_counter[m] += 1
        for d in clean_datasets:
            datasets_counter[d] += 1

        # Take the most informative sentence from the paper's excerpt for the combined category overview
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", ex_info["excerpt"]) if len(s.strip()) >= 20]
        lead_sent = sents[0] if sents else ex_info["excerpt"]
        year_tag = f" ({paper.year})" if paper.year else ""
        overview_parts.append(f"• {ex_info['paper_title']}{year_tag}: \"{lead_sent}\"")

    return {
        "overview": "\n\n".join(overview_parts),
        "methods": [m for m, _ in methods_counter.most_common(8)],
        "datasets": [d for d, _ in datasets_counter.most_common(6)],
        "papers": paper_excerpts,
    }


def compute_paper_hierarchy(
    papers: List[PaperMetadata],
    chunks_by_paper: Dict[str, List[TextChunk]],
    mined_by_paper: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Cluster papers into Macro-Categories (Groups) and optional nested Subcategories (Subgroups).

    Returns a dictionary containing:
    - 'paper_assignments': { paper_id: { 'group_id', 'group_label', 'subgroup_id', 'subgroup_label' } }
    - 'groups': list of group metadata objects (ordered for left-to-right canvas placement)
    """
    if not papers:
        return {"paper_assignments": {}, "groups": []}

    papers_by_id = {p.id: p for p in papers}
    paper_ids = [p.id for p in papers]

    tfidf_vecs = _build_paper_tfidf_vectors(papers, chunks_by_paper, mined_by_paper)
    phrases_by_paper = {
        p.id: _extract_candidate_phrases(
            p, chunks_by_paper.get(p.id, []), mined_by_paper.get(p.id, {})
        )
        for p in papers
    }

    # Build undirected citation adjacency set and shared-reference set
    direct_citations: Set[Tuple[str, str]] = set()
    cited_by_map: Dict[str, Set[str]] = {p.id: set() for p in papers}
    cites_map: Dict[str, Set[str]] = {p.id: set() for p in papers}

    for p in papers:
        mined = mined_by_paper.get(p.id, {})
        for target_id in mined.get("cited_paper_ids", []):
            if target_id in papers_by_id and target_id != p.id:
                pair = (p.id, target_id) if p.id < target_id else (target_id, p.id)
                direct_citations.add(pair)
                cites_map[p.id].add(target_id)
                cited_by_map[target_id].add(p.id)

    # Compute pairwise hybrid affinity (content + entities + citations)
    macro_affinity: Dict[Tuple[str, str], float] = {}
    sub_affinity: Dict[Tuple[str, str], float] = {}

    for i in range(len(paper_ids)):
        for j in range(i + 1, len(paper_ids)):
            u = paper_ids[i]
            v = paper_ids[j]
            key = (u, v) if u < v else (v, u)

            content_sim = _cosine_sim(tfidf_vecs[u], tfidf_vecs[v])

            methods_u = set(mined_by_paper.get(u, {}).get("methods", []))
            methods_v = set(mined_by_paper.get(v, {}).get("methods", []))
            datasets_u = set(mined_by_paper.get(u, {}).get("datasets", []))
            datasets_v = set(mined_by_paper.get(v, {}).get("datasets", []))

            shared_methods = len(methods_u.intersection(methods_v))
            shared_datasets = len(datasets_u.intersection(datasets_v))
            union_entities = max(
                1, len(methods_u | methods_v) + len(datasets_u | datasets_v)
            )
            entity_sim = min(
                1.0,
                (shared_methods * 1.5 + shared_datasets * 1.0) / union_entities,
            )
            if shared_methods >= 1:
                entity_sim = max(entity_sim, 0.35)

            has_direct_cite = 1.0 if key in direct_citations else 0.0
            co_citation_overlap = len(
                cites_map[u].intersection(cites_map[v])
            ) + len(cited_by_map[u].intersection(cited_by_map[v]))
            cite_sim = max(
                has_direct_cite,
                0.55 if co_citation_overlap >= 1 else 0.0,
            )

            # If a paper cites another paper ONLY in passing and has near-zero content/entity overlap,
            # dampen citation weight so unrelated papers aren't forced into the same group.
            if content_sim < 0.06 and entity_sim == 0.0:
                effective_cite_sim = cite_sim * 0.25
            else:
                effective_cite_sim = cite_sim

            combined_macro = (
                0.50 * content_sim
                + 0.30 * entity_sim
                + 0.20 * effective_cite_sim
            )
            # Sub-clustering emphasizes specific content and fine-grained method differences
            combined_sub = (
                0.65 * content_sim
                + 0.25 * entity_sim
                + 0.10 * effective_cite_sim
            )

            macro_affinity[key] = combined_macro
            sub_affinity[key] = combined_sub

    # Level 1: Macro-Categories (broad domain groups)
    macro_clusters = _agglomerative_cluster(
        paper_ids, macro_affinity, threshold=0.14
    )

    # Sort macro-clusters by size descending, then by earliest publication year
    macro_clusters.sort(
        key=lambda cl: (
            -len(cl),
            min((papers_by_id[pid].year or 9999) for pid in cl),
        )
    )

    paper_assignments: Dict[str, Dict[str, Any]] = {}
    groups_out: List[Dict[str, Any]] = []

    for g_idx, m_cluster in enumerate(macro_clusters, start=1):
        group_id = f"group_{g_idx}"
        group_label = _choose_cluster_label(
            m_cluster,
            macro_clusters,
            papers_by_id,
            phrases_by_paper,
            mined_by_paper,
            is_subgroup=False,
        )
        group_details = _build_cluster_topic_summary(
            m_cluster,
            papers_by_id,
            chunks_by_paper,
            mined_by_paper,
        )

        subgroups_out: List[Dict[str, Any]] = []

        # Level 2: Create nested Subgroups if the Macro-Group has >= 3 papers and splits meaningfully
        if len(m_cluster) >= 3:
            # Identify broad concepts/methods shared by >= 65% of papers in this macro-group so sub-clustering
            # focuses on sub-topic / variant differences within the macro-group
            macro_phrase_counts: Counter[str] = Counter()
            for pid in m_cluster:
                for ph, _ in phrases_by_paper.get(pid, []):
                    macro_phrase_counts[ph.lower()] += 1
            ubiquitous_phrases = {
                ph
                for ph, cnt in macro_phrase_counts.items()
                if cnt >= max(2, math.ceil(len(m_cluster) * 0.65))
            }

            intra_sub_affinity: Dict[Tuple[str, str], float] = {}
            for i_idx in range(len(m_cluster)):
                for j_idx in range(i_idx + 1, len(m_cluster)):
                    u = m_cluster[i_idx]
                    v = m_cluster[j_idx]
                    key = (u, v) if u < v else (v, u)
                    phrases_u = {
                        ph.lower()
                        for ph, _ in phrases_by_paper.get(u, [])
                        if ph.lower() not in ubiquitous_phrases
                    }
                    phrases_v = {
                        ph.lower()
                        for ph, _ in phrases_by_paper.get(v, [])
                        if ph.lower() not in ubiquitous_phrases
                    }
                    specific_overlap = len(phrases_u.intersection(phrases_v)) / max(
                        1, min(len(phrases_u), len(phrases_v))
                    )
                    content_s = _cosine_sim(tfidf_vecs[u], tfidf_vecs[v])
                    datasets_u = set(mined_by_paper.get(u, {}).get("datasets", []))
                    datasets_v = set(mined_by_paper.get(v, {}).get("datasets", []))
                    shared_ds = 0.25 if datasets_u.intersection(datasets_v) else 0.0
                    intra_sub_affinity[key] = (
                        0.45 * content_s + 0.40 * specific_overlap + 0.15 * shared_ds
                    )

            intra_vals = sorted(intra_sub_affinity.values())
            avg_intra = sum(intra_vals) / max(1, len(intra_vals))
            max_intra = intra_vals[-1] if intra_vals else 0.0
            min_intra = intra_vals[0] if intra_vals else 0.0

            # Only split into subgroups if there is meaningful internal variance or >= 4 papers
            spread = max_intra - min_intra
            if spread >= 0.06 or len(m_cluster) >= 4:
                # Target 2 to 3 cohesive sub-clusters
                adaptive_thresh = avg_intra + 0.10 * spread
                sub_clusters = _agglomerative_cluster(
                    m_cluster, intra_sub_affinity, threshold=adaptive_thresh
                )
            else:
                sub_clusters = [m_cluster]

            # Consolidate singletons into multi-clusters only when >= 2 sub-clusters remain
            if len(sub_clusters) > 2:
                multi_clusters = [c for c in sub_clusters if len(c) >= 2]
                singletons = [c[0] for c in sub_clusters if len(c) == 1]
                if len(multi_clusters) >= 2 and singletons:
                    remaining_singletons: List[List[str]] = []
                    for spid in singletons:
                        best_mc_idx = -1
                        best_mc_sim = -1.0
                        for mc_idx, mc in enumerate(multi_clusters):
                            avg_s = sum(
                                intra_sub_affinity.get(
                                    (spid, opid) if spid < opid else (opid, spid), 0.0
                                )
                                for opid in mc
                            ) / len(mc)
                            if avg_s > best_mc_sim:
                                best_mc_sim = avg_s
                                best_mc_idx = mc_idx
                        if best_mc_idx >= 0 and best_mc_sim >= avg_intra * 0.70:
                            multi_clusters[best_mc_idx].append(spid)
                        else:
                            remaining_singletons.append([spid])
                    sub_clusters = multi_clusters + remaining_singletons

            # Sort sub-clusters by earliest year so foundational sub-topics appear on the left
            sub_clusters.sort(
                key=lambda scl: (
                    min((papers_by_id[pid].year or 9999) for pid in scl),
                    -len(scl),
                )
            )

            if 2 <= len(sub_clusters) <= len(m_cluster):
                used_sub_labels: Set[str] = set()
                for s_idx, s_cluster in enumerate(sub_clusters, start=1):
                    subgroup_id = f"{group_id}_sub_{s_idx}"
                    sub_label = _choose_cluster_label(
                        s_cluster,
                        sub_clusters,
                        papers_by_id,
                        phrases_by_paper,
                        mined_by_paper,
                        is_subgroup=True,
                        parent_label=group_label,
                    )
                    if sub_label.lower() in used_sub_labels:
                        first_p = papers_by_id[s_cluster[0]]
                        sub_label = f"{sub_label} ({first_p.year or s_idx})"
                    used_sub_labels.add(sub_label.lower())

                    sub_details = _build_cluster_topic_summary(
                        s_cluster,
                        papers_by_id,
                        chunks_by_paper,
                        mined_by_paper,
                    )

                    subgroups_out.append(
                        {
                            "id": subgroup_id,
                            "label": sub_label,
                            "paper_ids": s_cluster,
                            "details": sub_details,
                        }
                    )
                    for pid in s_cluster:
                        paper_assignments[pid] = {
                            "group_id": group_id,
                            "group_label": group_label,
                            "group_details": group_details,
                            "subgroup_id": subgroup_id,
                            "subgroup_label": sub_label,
                            "subgroup_details": sub_details,
                        }

        if not subgroups_out:
            for pid in m_cluster:
                paper_assignments[pid] = {
                    "group_id": group_id,
                    "group_label": group_label,
                    "group_details": group_details,
                    "subgroup_id": None,
                    "subgroup_label": None,
                    "subgroup_details": None,
                }

        groups_out.append(
            {
                "id": group_id,
                "label": group_label,
                "paper_ids": m_cluster,
                "details": group_details,
                "subgroups": subgroups_out,
            }
        )

    return {
        "paper_assignments": paper_assignments,
        "groups": groups_out,
    }

