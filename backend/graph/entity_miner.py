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

# Concise scientific definitions for extracted concepts
ENTITY_DESCRIPTIONS: Dict[str, str] = {
    # Methods
    "Transformer": (
        "A sequence-to-sequence neural network architecture based solely on self-attention mechanisms, "
        "dispensing with recurrent (RNN) and convolutional layers to enable massive parallelization."
    ),
    "Self-Attention": (
        "An attention mechanism relating different positions of a single sequence in order to compute "
        "a contextualized representation of the sequence."
    ),
    "Scaled Dot-Product Attention": (
        "Core attention operation computing softmax(Q K^T / sqrt(d_k)) V, where the 1/sqrt(d_k) factor "
        "prevents dot products from growing too large in magnitude and vanishing softmax gradients."
    ),
    "Multi-Head Attention": (
        "Projects queries, keys, and values h times with different learned linear projections to attend "
        "jointly to information from different representation subspaces."
    ),
    "Positional Encoding": (
        "Injects token order information into sequence representations using fixed sinusoidal frequencies "
        "or learned position embeddings."
    ),
    "LoRA": (
        "Low-Rank Adaptation: a parameter-efficient fine-tuning method that freezes pre-trained model weights "
        "and injects trainable rank-decomposition matrices (B·A) into Transformer layers."
    ),
    "Low-Rank Decomposition": (
        "Constrains weight updates ΔW = B·A using low-rank matrices where rank r << min(d, k), drastically "
        "reducing trainable parameters and optimizer memory states."
    ),
    "BERT": (
        "Bidirectional Encoder Representations from Transformers: pre-trains deep bidirectional representations "
        "from unlabeled text by conditioning jointly on left and right context across all layers."
    ),
    "Masked Language Modeling": (
        "Self-supervised pre-training objective that masks 15% of input tokens ([MASK]) and trains the model "
        "to predict the original vocabulary IDs from bidirectional context."
    ),
    "Next Sentence Prediction": (
        "Binary classification pre-training task predicting whether Sentence B directly follows Sentence A "
        "in the source document corpus."
    ),
    "Rotary Position Embedding": (
        "RoPE: encodes absolute token position with a rotation matrix while naturally incorporating explicit "
        "relative position dependency into the self-attention inner product."
    ),
    "FlashAttention": (
        "An IO-aware exact attention algorithm that uses block tiling and online softmax in fast GPU on-chip "
        "SRAM to avoid materializing the O(N^2) attention matrix in slow GPU HBM memory."
    ),
    "IO-Aware Tiling": (
        "Partitions Q, K, V matrices into SRAM-resident tiles and fuses softmax normalization to reduce HBM "
        "memory reads/writes from O(N^2) to O(N)."
    ),
    # Datasets
    "WMT 2014": (
        "Workshop on Machine Translation 2014 benchmark (English-to-German and English-to-French) used to "
        "evaluate sequence transduction and translation quality."
    ),
    "GLUE": (
        "General Language Understanding Evaluation benchmark: a collection of diverse natural language "
        "understanding tasks (entailment, sentiment, similarity)."
    ),
    "MultiNLI": (
        "Multi-Genre Natural Language Inference corpus testing sentence-pair textual entailment across genres."
    ),
    "SQuAD": (
        "Stanford Question Answering Dataset: extractive reading comprehension benchmark scored by Exact Match and F1."
    ),
    "WikiSQL": (
        "Large-scale semantic parsing dataset converting natural language questions into SQL queries."
    ),
    "SAMSum": (
        "Abstractive dialogue summarization dataset containing messenger-style conversations."
    ),
    "WikiText-103": (
        "Long-term dependency language modeling benchmark extracted from verified Wikipedia articles."
    ),
    "Long-Range Arena": (
        "Benchmark suite (including Path-X) evaluating Transformer efficiency and accuracy on long sequences (1K–64K tokens)."
    ),
    # Metrics
    "BLEU": (
        "Bilingual Evaluation Understudy score measuring n-gram precision between machine-translated output and human references."
    ),
    "F1 Score": (
        "Harmonic mean of precision and recall, used to evaluate span-level question answering on SQuAD."
    ),
    "Accuracy": (
        "Percentage of exact correct predictions on classification, entailment (MultiNLI), or SQL generation benchmarks."
    ),
    "GPU Memory / VRAM": (
        "Peak GPU High Bandwidth Memory (HBM / VRAM) footprint consumed by model weights, activations, and optimizer states."
    ),
    "Training Speedup": (
        "Wall-clock training throughput improvement measured in FLOPs/sec or relative runtime reduction."
    ),
    "Parameter Efficiency": (
        "Ratio of downstream task performance to the number of trainable parameters updated during adaptation."
    ),
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


def find_entity_evidence_in_paper(
    entity_name: str,
    paper: PaperMetadata,
    chunks: List[TextChunk],
) -> Dict[str, Any]:
    """Find the best sentence in a paper explaining how that paper relates to `entity_name`."""
    patterns = (
        KNOWN_METHODS.get(entity_name)
        or KNOWN_DATASETS.get(entity_name)
        or KNOWN_METRICS.get(entity_name)
        or [re.escape(entity_name)]
    )

    best_sentence = ""
    best_page = 1

    # Search chunks for a sentence matching the entity pattern
    for ch in chunks:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", ch.text) if len(s.strip()) > 20]
        for sent in sentences:
            if any(re.search(pat, sent, flags=re.IGNORECASE) for pat in patterns):
                best_sentence = sent
                best_page = ch.page_number
                break
        if best_sentence:
            break

    if not best_sentence and paper.abstract:
        best_sentence = paper.abstract[:220] + ("..." if len(paper.abstract) > 220 else "")

    # Determine whether this paper originally introduces/proposes the concept or extends/builds on it
    title_lower = paper.title.lower()
    sent_lower = best_sentence.lower()
    is_originator = (
        entity_name.lower() in title_lower
        or (
            entity_name == "Scaled Dot-Product Attention" and "attention is all you need" in title_lower
        )
        or (
            entity_name == "Multi-Head Attention" and "attention is all you need" in title_lower
        )
        or (
            entity_name == "Low-Rank Decomposition" and "lora" in title_lower
        )
        or (
            entity_name in {"Masked Language Modeling", "Next Sentence Prediction"}
            and "bert" in title_lower
        )
        or (
            entity_name == "IO-Aware Tiling" and "flashattention" in title_lower
        )
        or any(
            phrase in sent_lower
            for phrase in ["we propose", "we introduce", "we call our particular"]
        )
    )

    role = "Introduces / Proposes" if is_originator else "Builds On / Evaluates"
    return {
        "paper_id": paper.id,
        "paper_title": paper.title,
        "year": paper.year,
        "role": role,
        "explanation": best_sentence or f"Referenced in {paper.title}.",
        "page": best_page,
    }


def get_entity_description(entity_name: str, entity_type: str) -> str:
    """Return a concise scientific explanation of what an entity is."""
    if entity_name in ENTITY_DESCRIPTIONS:
        return ENTITY_DESCRIPTIONS[entity_name]
    if entity_type == "Author":
        return f"Scientific researcher and co-author of indexed literature in this corpus."
    if entity_type == "Method":
        return f"{entity_name}: neural architecture or algorithmic technique extracted from the corpus."
    if entity_type == "Dataset":
        return f"{entity_name}: empirical evaluation dataset or benchmark suite."
    if entity_type == "Metric":
        return f"{entity_name}: quantitative evaluation metric reported in experiments."
    return ""


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

        if self.use_spacy_ner:
            nlp = get_spacy_nlp()
            doc = nlp(text[:5000])

            custom_method_matches = re.findall(
                r"\b([A-Z][A-Za-z0-9-]+(?:\s+[A-Z][A-Za-z0-9-]+){0,2}\s+(?:Attention|Network|Transformer|Adapter|Embedding|Classifier|Loss|Optimizer))\b",
                text,
            )
            for m in custom_method_matches:
                cleaned = m.strip()
                if 4 <= len(cleaned) <= 45 and cleaned not in methods:
                    methods.add(cleaned)

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
