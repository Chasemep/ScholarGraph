"""Pre-cache spaCy and HuggingFace Transformer models for offline-capable execution."""

import subprocess
import sys

SPACY_MODEL = "en_core_web_sm"
BI_ENCODER_MODEL = "all-MiniLM-L6-v2"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def ensure_spacy_model(model_name: str = SPACY_MODEL) -> None:
    """Download and verify the spaCy English NER pipeline."""
    import spacy

    try:
        spacy.load(model_name)
        print(f"[OK] spaCy model '{model_name}' is already installed.")
    except OSError:
        print(f"[INFO] Downloading spaCy model '{model_name}'...")
        subprocess.run(
            [sys.executable, "-m", "spacy", "download", model_name],
            check=True,
        )
        spacy.load(model_name)
        print(f"[OK] spaCy model '{model_name}' downloaded and verified.")


def ensure_transformer_models() -> None:
    """Download and pre-warm dense Bi-Encoder and Cross-Encoder models."""
    from sentence_transformers import CrossEncoder, SentenceTransformer

    print(f"[INFO] Pre-caching Bi-Encoder '{BI_ENCODER_MODEL}'...")
    bi_encoder = SentenceTransformer(BI_ENCODER_MODEL)
    vec = bi_encoder.encode(["ScholarGraph initialization verification"])
    assert vec.shape == (1, 384), f"Expected (1, 384) embedding shape, got {vec.shape}"
    print(f"[OK] Bi-Encoder '{BI_ENCODER_MODEL}' verified (dim=384).")

    print(f"[INFO] Pre-caching Cross-Encoder '{CROSS_ENCODER_MODEL}'...")
    cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
    scores = cross_encoder.predict([("query", "document passage")])
    assert len(scores) == 1, "Cross-Encoder failed sanity check"
    print(f"[OK] Cross-Encoder '{CROSS_ENCODER_MODEL}' verified.")


def main() -> None:
    """Run all model pre-caching steps."""
    ensure_spacy_model()
    ensure_transformer_models()
    print("[SUCCESS] All NLP & IR models are cached and ready.")


if __name__ == "__main__":
    main()

