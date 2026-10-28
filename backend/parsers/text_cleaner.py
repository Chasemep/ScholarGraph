"""Text cleaning, ligature expansion, de-hyphenation, and mathematical notation preservation (T038)."""

import re
import unicodedata

# Common typographic ligatures in PDFs that should be expanded to standard ASCII letters
LIGATURE_MAP = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\u2013": "-",
    "\u2014": " - ",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u00a0": " ",
}

# Canonical section header patterns in scientific papers
SECTION_PATTERNS = [
    ("Abstract", re.compile(r"^(?:abstract)$", re.IGNORECASE)),
    ("Introduction", re.compile(r"^(?:1\.?\s+|i\.?\s+)?introduction$", re.IGNORECASE)),
    (
        "Related Work",
        re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+|[ivx]+\.?\s+)?(?:related\s+work|background|preliminaries)$", re.IGNORECASE),
    ),
    (
        "Methods",
        re.compile(
            r"^(?:\d+(?:\.\d+)*\.?\s+|[ivx]+\.?\s+)?(?:method(?:s|ology)?|approach|model\s+architecture|proposed\s+method|algorithm|architecture)$",
            re.IGNORECASE,
        ),
    ),
    (
        "Experiments",
        re.compile(
            r"^(?:\d+(?:\.\d+)*\.?\s+|[ivx]+\.?\s+)?(?:experiments?|empirical\s+evaluation|experimental\s+setup|evaluation)$",
            re.IGNORECASE,
        ),
    ),
    (
        "Results",
        re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+|[ivx]+\.?\s+)?(?:results?(?:\s+and\s+discussion)?|analysis|ablation\s+study)$", re.IGNORECASE),
    ),
    (
        "Conclusion",
        re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+|[ivx]+\.?\s+)?(?:conclusions?(?:\s+and\s+future\s+work)?|summary|discussion)$", re.IGNORECASE),
    ),
    (
        "References",
        re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+|[ivx]+\.?\s+)?(?:references|bibliography)$", re.IGNORECASE),
    ),
]

NUMBERED_HEADING_REGEX = re.compile(
    r"^([1-9]\d?(?:\.\d+)*)\.?\s+([A-Z][A-Za-z0-9\s\-:,&()]{2,55})$"
)


def clean_scientific_text(raw_text: str) -> str:
    """Normalize PDF text while preserving Greek symbols (α, β, Δ, Θ, λ) and mathematical formulas."""
    if not raw_text:
        return ""

    # Expand typographic ligatures first
    text = raw_text
    for lig, replacement in LIGATURE_MAP.items():
        text = text.replace(lig, replacement)

    # Strip PDF font CID fallback markers such as (cid:2)
    text = re.sub(r"\(cid:\d+\)", "", text)

    # Normalize Unicode with NFC (keeps Greek letters α, β, γ, Δ, Θ, Ω intact)
    text = unicodedata.normalize("NFC", text)

    # Remove control characters except standard whitespace
    text = "".join(
        ch for ch in text if ch in ("\n", "\t", " ") or unicodedata.category(ch)[0] != "C"
    )

    # Rejoin words hyphenated across line breaks (e.g., "trans-\nformer" or "trans- former" -> "transformer")
    # while keeping genuine compound terms like "Self-Attention", "GPT-3", "low-rank"
    text = re.sub(r"([a-z]{3,})-\s*\n\s*([a-z]{2,})", r"\1\2", text)
    text = re.sub(r"([a-z]{3,})-\s+([a-z]{3,})", lambda m: _rejoin_if_broken_word(m.group(1), m.group(2)), text)

    # Collapse redundant whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


KNOWN_HYPHENATED_PREFIXES = {
    "self", "multi", "low", "high", "pre", "non", "cross", "co", "sub",
    "fine", "long", "short", "end", "state", "wall", "on", "off", "two",
    "three", "one", "zero", "few", "meta", "auto", "bi", "tri", "semi",
    "io", "left", "right", "top", "bottom", "full", "half", "rank",
}


def _rejoin_if_broken_word(prefix: str, suffix: str) -> str:
    """Rejoin a hyphen+space pair if it looks like a line-wrap hyphenation rather than a compound modifier."""
    if prefix.lower() in KNOWN_HYPHENATED_PREFIXES:
        return f"{prefix}-{suffix}"
    return f"{prefix}{suffix}"


def categorize_section_heading(line_text: str) -> str | None:
    """Identify if a single line of text is a paper section heading and return its normalized name."""
    if not line_text:
        return None
    raw_stripped = line_text.strip()
    is_bracketed = raw_stripped.startswith("[") and raw_stripped.endswith("]")
    cleaned = raw_stripped.strip("[]").strip()
    if len(cleaned) < 3 or len(cleaned) > 68:
        return None

    for canonical_name, pattern in SECTION_PATTERNS:
        if pattern.match(cleaned):
            return canonical_name

    if is_bracketed and sum(1 for c in cleaned if c.isalpha()) >= 4:
        return cleaned

    m = NUMBERED_HEADING_REGEX.match(cleaned)
    if m:
        sec_num, sec_title = m.group(1), m.group(2).strip()
        # Avoid matching table data lines where the title is mostly numbers
        alpha_count = sum(1 for c in sec_title if c.isalpha())
        if alpha_count >= 4:
            for canonical_name, pattern in SECTION_PATTERNS:
                if pattern.match(sec_title):
                    return canonical_name
            return f"{sec_num} {sec_title}"

    return None

