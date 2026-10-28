"""Deterministic multi-page PDF generator for the 5 core open-access seed papers.

Generates standards-compliant PDF 1.4 documents with rich scientific sections,
bibliographic headers, and multi-page text streams so pdfplumber and pypdf
extract exact character/word bounding boxes offline and in CI/CD environments.
"""

from pathlib import Path
from typing import Dict, List, Any

from backend.config import settings

SEED_PAPERS_MANIFEST: List[Dict[str, Any]] = [
    {
        "id": "paper_vaswani2017",
        "filename": "vaswani2017_attention.pdf",
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones", "Aidan N. Gomez", "Lukasz Kaiser", "Illia Polosukhin"],
        "year": 2017,
        "doi": "10.48550/arXiv.1706.03762",
        "pages": [
            {
                "section": "Abstract",
                "paragraphs": [
                    "Attention Is All You Need",
                    "Authors: Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin (2017)",
                    "Abstract: The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
                    "Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU.",
                ],
            },
            {
                "section": "Model Architecture & Scaled Dot-Product Attention",
                "paragraphs": [
                    "3.2 Attention: An attention function can be described as mapping a query and a set of key-value pairs to an output, where the query, keys, values, and output are all vectors. We call our particular attention Scaled Dot-Product Attention. The input consists of queries and keys of dimension d_k, and values of dimension d_v.",
                    "We compute the dot products of the query with all keys, divide each by the square root of d_k (1 / sqrt(d_k) scaling factor), and apply a softmax function to obtain the weights on the values. For large values of d_k, the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients.",
                    "Multi-Head Attention allows the model to jointly attend to information from different representation subspaces at different positions. With a single attention head, averaging inhibits this. In this work we employ h = 8 parallel attention layers, or heads, with d_k = d_v = d_model / h = 64.",
                ],
            },
            {
                "section": "Positional Encoding & Experimental Results",
                "paragraphs": [
                    "3.5 Positional Encoding: Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject some information about the relative or absolute position of the tokens in the sequence. We use sine and cosine functions of different frequencies added to the input embeddings.",
                    "5.1 Machine Translation Results: On the WMT 2014 English-to-German translation task, the big Transformer model (Transformer big) outperforms the best previously reported models including ensembles by more than 2.0 BLEU, establishing a new state-of-the-art BLEU score of 28.4 after training for 3.5 days on 8 P100 GPUs.",
                    "On the WMT 2014 English-to-French translation task, our big model achieves a BLEU score of 41.8, outperforming all of the previously published single models, at less than 1/4 the training cost of the previous state-of-the-art model.",
                ],
            },
        ],
    },
    {
        "id": "paper_hu2021",
        "filename": "hu2021_lora.pdf",
        "title": "LoRA: Low-Rank Adaptation of Large Language Models",
        "authors": ["Edward J. Hu", "Yelong Shen", "Phillip Wallis", "Zeyuan Allen-Zhu", "Yuanzhi Li", "Shean Wang", "Lu Wang", "Weizhu Chen"],
        "year": 2021,
        "doi": "10.48550/arXiv.2106.09685",
        "pages": [
            {
                "section": "Abstract",
                "paragraphs": [
                    "LoRA: Low-Rank Adaptation of Large Language Models",
                    "Authors: Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang, Weizhu Chen (2021)",
                    "Abstract: An important paradigm of natural language processing consists of large-scale pre-training on general domain data and adaptation to particular tasks or domains. As we pre-train larger models, full fine-tuning, which retrains all model parameters, becomes less feasible. Using GPT-3 175B as an example, deploying independent instances of fine-tuned models, each with 175B parameters, is prohibitively expensive.",
                    "We propose Low-Rank Adaptation, or LoRA, which freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture, greatly reducing the number of trainable parameters for downstream tasks. Compared to GPT-3 175B fine-tuned with Adam, LoRA can reduce the number of trainable parameters by 10,000 times and the GPU memory requirement by 3-fold.",
                ],
            },
            {
                "section": "Low-Rank Parameterized Update Matrices",
                "paragraphs": [
                    "4.1 Low-Rank Parameterized Update Matrices: A neural network contains many dense layers which perform matrix multiplication. The weight matrices in these layers typically have full-rank. When adapting to a specific task, pre-trained language models have a low intrinsic dimension and can still learn efficiently despite a random projection to a smaller subspace.",
                    "For a pre-trained weight matrix W_0 in R^(d x k), we constrain its update by representing the latter with a low-rank decomposition W_0 + Delta W = W_0 + B A, where B in R^(d x r), A in R^(r x k), and the rank r << min(d, k). During training, W_0 is frozen and does not receive gradient updates, while A and B contain trainable parameters.",
                    "We use a random Gaussian initialization for A and zero for B, so Delta W = B A is zero at the beginning of training. Unlike Adapters, LoRA introduces zero additional inference latency because the trainable matrices B A can be explicitly merged with the frozen weights W_0 during deployment.",
                ],
            },
            {
                "section": "Empirical Evaluation on GLUE and WikiSQL",
                "paragraphs": [
                    "5 Empirical Experiments: We evaluate the downstream task performance of LoRA on RoBERTa, DeBERTa, GPT-2, and GPT-3 175B across the GLUE benchmark, WikiSQL, and SAMSum datasets. In the Transformer architecture, we follow Vaswani et al. (2017) and apply LoRA to the Self-Attention projection matrices W_q and W_v.",
                    "On GPT-3 175B, LoRA matches or exceeds the full fine-tuning baseline on WikiSQL (achieving 74.0% accuracy) and MultiNLI (achieving 91.7% accuracy) while updating only 4.7M parameters compared to 175,255M parameters in full fine-tuning, reducing VRAM memory consumption from 1.2 TB to 350 GB.",
                ],
            },
        ],
    },
    {
        "id": "paper_devlin2019",
        "filename": "devlin2019_bert.pdf",
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
        "year": 2019,
        "doi": "10.48550/arXiv.1810.04805",
        "pages": [
            {
                "section": "Abstract",
                "paragraphs": [
                    "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
                    "Authors: Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova (2019)",
                    "Abstract: We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.",
                    "As a result, the pre-trained BERT model can be fine-tuned with just one additional output layer to create state-of-the-art models for a wide range of tasks, such as question answering and language inference, without substantial task-specific architecture modifications.",
                ],
            },
            {
                "section": "Masked Language Modeling & Next Sentence Prediction",
                "paragraphs": [
                    "3.1 Pre-training BERT: Building on the Transformer encoder architecture proposed by Vaswani et al. (2017), we pre-train BERT using two unsupervised tasks: Masked Language Modeling (MLM) and Next Sentence Prediction (NSP). In Masked LM, we randomly mask 15% of all WordPiece tokens in each sequence and predict the masked tokens.",
                    "For the 15% of tokens selected for masking, we replace the token with the [MASK] token 80% of the time, a random token 10% of the time, and the unchanged token 10% of the time. Next Sentence Prediction trains a binary classifier to determine whether sentence B actually follows sentence A in the pre-training corpus.",
                ],
            },
            {
                "section": "GLUE & SQuAD Benchmark Results",
                "paragraphs": [
                    "4 Experiments: BERT obtains new state-of-the-art results on eleven natural language processing tasks. It pushes the GLUE benchmark score to 80.5% (7.7% point absolute improvement), MultiNLI accuracy to 86.7% (4.6% absolute improvement), SQuAD v1.1 question answering Test F1 to 93.2 (1.5 point absolute improvement), and SQuAD v2.0 Test F1 to 83.1 (5.1 point absolute improvement).",
                ],
            },
        ],
    },
    {
        "id": "paper_su2021",
        "filename": "su2021_roformer.pdf",
        "title": "RoFormer: Enhanced Transformer with Rotary Position Embedding",
        "authors": ["Jianlin Su", "Yu Lu", "Shengfeng Pan", "Ahmed Murtadha", "Bo Wen", "Yunfeng Liu"],
        "year": 2021,
        "doi": "10.48550/arXiv.2104.09864",
        "pages": [
            {
                "section": "Abstract",
                "paragraphs": [
                    "RoFormer: Enhanced Transformer with Rotary Position Embedding",
                    "Authors: Jianlin Su, Yu Lu, Shengfeng Pan, Ahmed Murtadha, Bo Wen, Yunfeng Liu (2021)",
                    "Abstract: Position encoding recently has shown to be effective in the Transformer architecture. It enables valuable supervision for dependency modeling between elements at different positions of the sequence. We propose a novel method named Rotary Position Embedding (RoPE) to effectively leverage the positional information.",
                    "Specifically, the proposed RoPE encodes the absolute position with a rotation matrix and meanwhile incorporates the explicit relative position dependency in self-attention formulation. Notably, RoPE enables valuable properties, including the flexibility of sequence length, decaying inter-token dependency with increasing relative distances, and the capability of equipping the linear self-attention with relative position encoding.",
                ],
            },
            {
                "section": "Rotary Position Embedding Formulation",
                "paragraphs": [
                    "3.2 Rotary Position Embedding (RoPE): Unlike the additive sinusoidal positional encoding introduced in Vaswani et al. (2017) or the learned absolute position embeddings used in Devlin et al. (2019) BERT, RoPE multiplies the query and key representations by an orthogonal rotation matrix R_(Theta, m)^d parameterized by token position index m.",
                    "Because the inner product q_m^T k_n depends solely on the relative distance (m - n) and the token representations, RoPE naturally injects relative position awareness directly into Self-Attention without altering value vectors or requiring O(N^2) relative position bias tables.",
                ],
            },
            {
                "section": "Long-Context Extrapolation & Experiments",
                "paragraphs": [
                    "4 Experiments: Evaluating RoFormer on WMT 2014 English-to-German translation (achieving 27.5 BLEU on Transformer base) and pre-training on BERT downstream GLUE benchmarks demonstrates faster convergence and superior long-sequence extrapolation beyond 512 tokens compared to absolute positional encodings.",
                ],
            },
        ],
    },
    {
        "id": "paper_dao2022",
        "filename": "dao2022_flashattention.pdf",
        "title": "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness",
        "authors": ["Tri Dao", "Daniel Y. Fu", "Stefano Ermon", "Atri Rudra", "Christopher Re"],
        "year": 2022,
        "doi": "10.48550/arXiv.2205.14135",
        "pages": [
            {
                "section": "Abstract",
                "paragraphs": [
                    "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness",
                    "Authors: Tri Dao, Daniel Y. Fu, Stefano Ermon, Atri Rudra, Christopher Re (2022)",
                    "Abstract: Transformers are slow and memory-hungry on long sequences, since the time and memory complexity of self-attention are quadratic in sequence length. Approximate attention methods have attempted to address this problem by trading off model quality to reduce the compute complexity, but often do not achieve wall-clock speedup.",
                    "We argue that a missing principle is making attention algorithms IO-aware—that is, carefully accounting for reads and writes between levels of GPU memory. We propose FlashAttention, an IO-aware exact attention algorithm that uses tiling to reduce the number of memory reads/writes between GPU high bandwidth memory (HBM) and GPU on-chip SRAM.",
                ],
            },
            {
                "section": "IO-Aware Tiling & Online Softmax Recomputation",
                "paragraphs": [
                    "3 FlashAttention Algorithm: Standard Self-Attention (Vaswani et al., 2017) materializes the N x N attention matrix S = Q K^T and P = softmax(S) in slow GPU High Bandwidth Memory (HBM), requiring O(N^2) memory accesses. FlashAttention splits inputs Q, K, V into blocks, loads them from HBM into fast on-chip SRAM, and computes exact attention using online softmax scaling without ever materializing the intermediate N x N attention matrix in HBM.",
                    "During the backward pass, by storing the output O and the softmax normalization statistics (m, l) in HBM, FlashAttention recomputes the attention blocks on-chip in SRAM, reducing HBM memory complexity from O(N^2) to linear O(N) in sequence length N while producing the exact same mathematical output as standard attention.",
                ],
            },
            {
                "section": "Wall-Clock Speedup & Benchmark Results",
                "paragraphs": [
                    "4 Empirical Validation: FlashAttention trains BERT-large (Devlin et al., 2019) 15% faster than the MLPerf 1.1 training speed record, speeds up GPT-2 training by 3x over HuggingFace and 1.7x over Megatron-LM on WikiText-103, and improves long-range arena (LRA) Path-X accuracy to 61.4% by scaling context length to 16K and 64K tokens.",
                ],
            },
        ],
    },
]


def _escape_pdf_text(text: str) -> str:
    """Escape parentheses and backslashes for PDF string literals."""
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("—", "-")
    )


def _wrap_text(text: str, max_chars: int = 88) -> List[str]:
    """Wrap a paragraph into lines of at most max_chars characters."""
    words = text.split()
    lines: List[str] = []
    current: List[str] = []
    cur_len = 0
    for w in words:
        if current and cur_len + 1 + len(w) > max_chars:
            lines.append(" ".join(current))
            current = [w]
            cur_len = len(w)
        else:
            current.append(w)
            cur_len += len(w) + (1 if len(current) > 1 else 0)
    if current:
        lines.append(" ".join(current))
    return lines


def build_pdf_bytes(paper_spec: Dict[str, Any]) -> bytes:
    """Construct a valid multi-page PDF 1.4 binary document with Helvetica font and positioned paragraphs."""
    pages_spec = paper_spec["pages"]
    num_pages = len(pages_spec)

    # Object IDs:
    # 1: Catalog
    # 2: Pages
    # 3: Font (/F1 Helvetica)
    # 4..(3 + num_pages): Page objects
    # (4 + num_pages)..(3 + 2*num_pages): Content stream objects
    objects: Dict[int, bytes] = {}

    page_obj_ids = [4 + i for i in range(num_pages)]
    content_obj_ids = [4 + num_pages + i for i in range(num_pages)]

    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>".encode("latin-1")
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    for idx, page_data in enumerate(pages_spec):
        p_id = page_obj_ids[idx]
        c_id = content_obj_ids[idx]

        # Build content stream commands with distinct vertical spacing between paragraphs
        stream_lines = ["BT", "/F1 11 Tf"]
        y_cursor = 730

        # Section header
        section_header = f"[{page_data['section']}]"
        stream_lines.append(f"1 0 0 1 54 {y_cursor} Tm")
        stream_lines.append(f"({_escape_pdf_text(section_header)}) Tj")
        y_cursor -= 28

        for para in page_data["paragraphs"]:
            wrapped = _wrap_text(para, max_chars=84)
            for line in wrapped:
                stream_lines.append(f"1 0 0 1 54 {y_cursor} Tm")
                stream_lines.append(f"({_escape_pdf_text(line)}) Tj")
                y_cursor -= 15
            y_cursor -= 18  # Extra gap between paragraphs so bounding boxes separate cleanly

        stream_lines.append("ET")
        stream_body = "\n".join(stream_lines).encode("latin-1", errors="replace")

        objects[c_id] = (
            f"<< /Length {len(stream_body)} >>\nstream\n".encode("latin-1")
            + stream_body
            + b"\nendstream"
        )
        objects[p_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {c_id} 0 R >>"
        ).encode("latin-1")

    # Assemble PDF with cross-reference table
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: Dict[int, int] = {}
    max_obj_id = max(objects.keys())

    for obj_id in range(1, max_obj_id + 1):
        offsets[obj_id] = len(out)
        out.extend(f"{obj_id} 0 obj\n".encode("latin-1"))
        out.extend(objects[obj_id])
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    out.extend(f"xref\n0 {max_obj_id + 1}\n".encode("latin-1"))
    out.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, max_obj_id + 1):
        out.extend(f"{offsets[obj_id]:010d} 00000 n \n".encode("latin-1"))

    out.extend(
        (
            f"trailer\n<< /Size {max_obj_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin-1")
    )
    return bytes(out)


def ensure_seed_pdfs(target_dir: Path | None = None) -> List[Path]:
    """Generate all 5 seed PDF files into data/papers/ if missing or regenerate them."""
    out_dir = Path(target_dir) if target_dir else Path(settings.papers_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: List[Path] = []

    for paper_spec in SEED_PAPERS_MANIFEST:
        pdf_path = out_dir / paper_spec["filename"]
        pdf_bytes = build_pdf_bytes(paper_spec)
        pdf_path.write_bytes(pdf_bytes)
        generated_paths.append(pdf_path)

    return generated_paths


if __name__ == "__main__":
    paths = ensure_seed_pdfs()
    for p in paths:
        print(f"[OK] Generated seed PDF: {p.name} ({p.stat().st_size} bytes)")

