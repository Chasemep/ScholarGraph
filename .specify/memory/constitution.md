<!--
Sync Impact Report:
- Version change: initial scaffold -> 1.0.0
- List of modified principles:
  - PRINCIPLE_1: [PRINCIPLE_1_NAME] -> I. Grounded Synthesis & Zero-Hallucination Invariant (NON-NEGOTIABLE)
  - PRINCIPLE_2: [PRINCIPLE_2_NAME] -> II. Decoupled 4-Tier Architecture
  - PRINCIPLE_3: [PRINCIPLE_3_NAME] -> III. Hybrid Retrieval Supremacy
  - PRINCIPLE_4: [PRINCIPLE_4_NAME] -> IV. Test-Driven Verification & Benchmark Gates
  - PRINCIPLE_5: [PRINCIPLE_5_NAME] -> V. Academic Reproducibility & Executability
- Added sections:
  - Architectural Standards & Constraints (Data Schema & Contracts, Knowledge Graph Modeling, User Interface & Accessibility)
  - Quality Gates & Verification Standards (Gates 1-4)
- Removed sections: None
- Follow-up TODOs: None
-->

# ScholarGraph Constitution

## Core Principles

### I. Grounded Synthesis & Zero-Hallucination Invariant (NON-NEGOTIABLE)
- Every assertion, metric, and comparative summary produced by the platform must be strictly grounded in the ingested literature.
- Free-form generative speculation is prohibited. Every synthesized claim must carry deterministic citation provenance linking directly to an ingested paper ID, page number, and bounding-box coordinates `[page, x, y, width, height]`.
- If the retrieved context is insufficient or silent regarding a query, the system must deterministically output an explicit "insufficient context" message rather than extrapolate.

### II. Decoupled 4-Tier Architecture
The system must maintain strict separation of concerns across four tiers:
1. **Tier 1 (Presentation):** React + Vite, Tailwind CSS, Cytoscape.js (graph canvas), PDF.js (document rendering and bounding-box highlights).
2. **Tier 2 (Application API):** FastAPI backend, Pydantic v2 data models for request/response validation, asynchronous background processing for document ingestion.
3. **Tier 3 (AI & Modeling):** Dense vector embeddings (`all-MiniLM-L6-v2`), BM25 sparse keyword index, Cross-Encoder neural re-ranking (`ms-marco-MiniLM-L-6-v2`), spaCy NER (`en_core_web_sm`), and NetworkX graph modeling.
4. **Tier 4 (Persistence):** ChromaDB (vector embeddings), SQLite (relational paper and citation metadata), and local document storage.

### III. Hybrid Retrieval Supremacy
- Dense vector similarity alone is insufficient for scientific text containing exact formulas, mathematical notation, acronyms, and author names.
- All literature searches must execute a dual-retrieval pipeline combining BM25 keyword matching with ChromaDB vector search.
- Candidate passages must be merged using Reciprocal Rank Fusion (RRF) and re-ranked using a Cross-Encoder prior to LLM context construction.

### IV. Test-Driven Verification & Benchmark Gates
- Every backend feature must be accompanied by automated `pytest` unit and integration tests before task completion.
- Quantitative Information Retrieval benchmarks are non-negotiable:
  - **Retrieval Precision:** Mean Reciprocal Rank (MRR@5) >= 0.85 on the standardized validation question suite.
  - **Query Latency:** Sub-2.0s retrieval, sub-4.0s full synthesis.
  - **Hallucination Rate:** 0.0% ungrounded assertions.

### V. Academic Reproducibility & Executability
- In accordance with Course Project Guidelines §3, the application must be executable out of the box with zero specialized access or proprietary hardware requirements.
- The project must bundle a seed dataset of 5–8 high-impact open-access papers (e.g., Attention Is All You Need, LoRA, BERT) and automated setup scripts so an evaluator can clone, install, and run the complete system in under 5 minutes.

## Architectural Standards & Constraints

### 1. Data Schema & Contracts
- All API contracts must be strictly typed using Pydantic v2 schemas (`backend/models/`).
- Responses must use standard HTTP status codes, structured JSON payloads, and descriptive error messages (`detail` field).
- Ingestion pipelines must maintain document coordinate integrity: text chunks must store page numbers and paragraph bounding boxes for PDF.js highlight synchronization.

### 2. Knowledge Graph Modeling
- The knowledge graph schema must support five core entity types: `Paper`, `Author`, `Method`, `Dataset`, and `Metric`.
- Edges must represent typed relationships: `AUTHORED`, `PROPOSES`, `EVALUATES_ON`, and `CITES`.
- Graph endpoints must serialize topologies into Cytoscape.js-compliant JSON formats (`{ elements: { nodes: [...], edges: [...] } }`).

### 3. User Interface & Accessibility
- The presentation layer must provide a responsive split-screen research canvas:
  - Left panel: Multi-paper comparative Q&A, entity search, and clickable citation tokens.
  - Right panel: Synchronized PDF viewer jumping to exact pages and applying luminous bounding-box highlights upon clicking a citation.
  - Graph modal/canvas: Interactive Cytoscape network with zoom, pan, node expansion, and topic filtering.

## Quality Gates & Verification Standards

1. **Gate 1 (Ingestion):** PDF parser must extract title, abstract, sections, and bounding coordinates without losing character encoding.
2. **Gate 2 (RAG Precision):** Retrieval pipeline must pass automated MRR@5 evaluations exceeding 0.85.
3. **Gate 3 (API Contract):** All FastAPI endpoints must pass OpenAPI schema validation and automated integration tests.
4. **Gate 4 (Report Alignment):** Every architectural module implemented must produce metrics, diagrams, and test tables directly usable in the final >= 20-page Software Design I technical report.

## Governance

- **Supremacy:** This constitution supersedes all ad-hoc implementation choices. Any proposed feature that violates the zero-hallucination invariant or the 4-tier separation is rejected by default.
- **Spec-Driven Lifecycle:** All functional work must follow the Spec Kit sequence: `/specify` -> `/plan` -> `/tasks` -> `/implement`.
- **Amendments:** Modifying core principles requires updating this document, bumping the version number, and providing an explicit architectural rationale.

**Version**: 1.0.0 | **Ratified**: 2026-10-28 | **Last Amended**: 2026-10-28
