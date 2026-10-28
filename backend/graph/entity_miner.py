"""Scientific entity extraction pipeline using spaCy (en_core_web_sm) and domain pattern matchers."""

import re
from typing import Any, Dict, List, Set

from backend.models.paper import PaperMetadata, TextChunk

_shared_nlp: Any = None


def get_spacy_nlp():
    """Lazy-load and cache the spaCy en_core_web_sm pipeline (with blank('en') fallback)."""
    global _shared_nlp
    if _shared_nlp is None:
        import spacy

        try:
            _shared_nlp = spacy.load("en_core_web_sm", disable=["lemmatizer"])
        except OSError:
            _shared_nlp = spacy.blank("en")
    return _shared_nlp


# Canonical scientific Method, Dataset, and Metric lexicons + regex patterns
KNOWN_METHODS: Dict[str, List[str]] = {
    "Transformer": [r"\btransformer(?:s)?\b"],
    "Self-Attention": [r"\bself-attention\b", r"\battention mechanism(?:s)?\b"],
    "Scaled Dot-Product Attention": [r"\bscaled dot-product attention\b"],
    "Multi-Head Attention": [r"\bmulti-head attention\b"],
    "Positional Encoding": [r"\bpositional encoding(?:s)?\b", r"\bsinusoidal positional\b"],
    "LoRA": [r"\blora\b", r"\blow-rank adaptation\b"],
    "Low-Rank Decomposition": [r"\blow-rank decomposition\b", r"\brank decomposition matrices\b"],
    "BERT": [r"\bbert\b", r"\bbidirectional encoder representations\b"],
    "Masked Language Modeling": [r"\bmasked language model(?:ing)?\b", r"\bmlm\b"],
    "Next Sentence Prediction": [r"\bnext sentence prediction\b", r"\bnsp\b"],
    "Rotary Position Embedding": [r"\brotary position embedding(?:s)?\b", r"\brope\b", r"\broformer\b"],
    "FlashAttention": [r"\bflashattention\b"],
    "IO-Aware Tiling": [r"\bio-aware\b", r"\btiling\b", r"\bonline softmax\b"],
}

KNOWN_DATASETS: Dict[str, List[str]] = {
    "WMT 2014": [r"\bwmt\s*2014\b", r"\bwmt14\b"],
    "GLUE": [r"\bglue\b"],
    "MultiNLI": [r"\bmultinli\b", r"\bmnli\b"],
    "SQuAD": [r"\bsquad(?:\s*v[12]\.[01])?\b"],
    "WikiSQL": [r"\bwikisql\b"],
    "SAMSum": [r"\bsamsum\b"],
    "WikiText-103": [r"\bwikitext-103\b", r"\bwikitext\b"],
    "Long-Range Arena": [r"\blong-range arena\b", r"\bpath-x\b"],
}

KNOWN_METRICS: Dict[str, List[str]] = {
    "BLEU": [r"\bbleu\b"],
    "F1 Score": [r"\btest f1\b", r"\bf1(?:\s+score)?\b"],
    "Accuracy": [r"\baccuracy\b"],
    "GPU Memory / VRAM": [r"\bgpu memory\b", r"\bvram\b", r"\bhbm\b"],
    "Training Speedup": [r"\bwall-clock speedup\b", r"\btraining speed\b", r"\b3x\b", r"\b15%\s+faster\b"],
    "Parameter Efficiency": [r"\btrainable parameters\b", r"\b10,000 times\b"],
}

# Author surname citation cues to detect cross-paper CITES edges
CITATION_CUES: Dict[str, List[str]] = {
    "paper_vaswani2017": [r"\bvaswani\b", r"\battention is all you need\b"],
    "paper_devlin2019": [r"\bdevlin\b", r"\bbert-large\b"],
    "paper_hu2021": [r"\bhu et al\b"],
    "paper_su2021": [r"\bsu et al\b"],
    "paper_dao2022": [r"\bdao et al\b"],
}


def _match_canonical_terms(text: str, lexicon: Dict[str, List[str]]) -> List[str]:
    """Match canonical entity names against text using case-insensitive regex patterns."""
    matched: List[str] = []
    for canonical_name, patterns in lexicon.items():
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                matched.append(canonical_name)
                break
    return matched


class ScientificEntityMiner:
    """Extracts structured scientific entities (Paper, Author, Method, Dataset, Metric) and citations."""

    def __init__(self, use_spacy_ner: bool = True) -> None:
        self.use_spacy_ner = use_spacy_ner

    def extract_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract Methods, Datasets, Metrics, and cited paper IDs from a single text string."""
        if not text or not text.strip():
            return {"methods": [], "datasets": [], "metrics": [], "cited_paper_ids": []}

        methods = set(_match_canonical_terms(text, KNOWN_METHODS))
        datasets = set(_match_canonical_terms(text, KNOWN_DATASETS))
        metrics = set(_match_canonical_terms(text, KNOWN_METRICS))
        cited_papers = set(_match_canonical_terms(text, CITATION_CUES))

        # Supplement with spaCy NER / noun-chunk pattern mining for custom user-uploaded papers
        if self.use_spacy_ner:
            nlp = get_spacy_nlp()
            doc = nlp(text[:5000])

            # Extract capitalized algorithmic / architecture terms ending in Model/Network/Attention/Adapter/Loss
            custom_method_matches = re.findall(
                r"\b([A-Z][A-Za-z0-9-]+(?:\s+[A-Z][A-Za-z0-9-]+){0,2}\s+(?:Attention|Network|Transformer|Adapter|Embedding|Classifier|Loss|Optimizer))\b",
                text,
            )
            for m in custom_method_matches:
                cleaned = m.strip()
                if 4 <= len(cleaned) <= 45 and cleaned not in methods:
                    methods.add(cleaned)

            # Check spaCy ORG/PRODUCT entities for benchmark dataset cues
            for ent in getattr(doc, "ents", []):
                if ent.label_ in {"PRODUCT", "WORK_OF_ART"} and any(
                    kw in ent.text.lower() for kw in ["dataset", "corpus", "benchmark"]
                ):
                    datasets.add(ent.text.strip())

        return {
            "methods": sorted(methods),
            "datasets": sorted(datasets),
            "metrics": sorted(metrics),
            "cited_paper_ids": sorted(cited_papers),
        }

    def extract_for_paper(
        self,
        paper: PaperMetadata,
        chunks: List[TextChunk],
    ) -> Dict[str, Any]:
        """Aggregate all extracted entities and cross-citations across a paper and its chunks."""
        methods: Set[str] = set()
        datasets: Set[str] = set()
        metrics: Set[str] = set()
        cited_paper_ids: Set[str] = set()

        combined_texts = [paper.title, paper.abstract or ""] + [c.text for c in chunks]
        full_text = "\n".join(t for t in combined_texts if t)

        extracted = self.extract_from_text(full_text)
        methods.update(extracted["methods"])
        datasets.update(extracted["datasets"])
        metrics.update(extracted["metrics"])
        for cid in extracted["cited_paper_ids"]:
            if cid != paper.id:
                cited_paper_ids.add(cid)

        return {
            "paper_id": paper.id,
            "title": paper.title,
            "authors": list(paper.authors),
            "year": paper.year,
            "methods": sorted(methods),
            "datasets": sorted(datasets),
            "metrics": sorted(metrics),
            "cited_paper_ids": sorted(cited_paper_ids),
        }


entity_miner = ScientificEntityMiner()

