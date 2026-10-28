# Implementation Plan: Core Grounded Literature Research Platform

**Branch**: `001-core-research-platform` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-core-research-platform/spec.md`

---

## Summary

The **Core Grounded Literature Research Platform** realizes a dual-engine architecture to address academic literature overload and generative AI hallucinations:
1. **Pillar 1: Grounded Hybrid RAG Pipeline**: Combines dense vector similarity (`all-MiniLM-L6-v2` in ChromaDB) and sparse lexical search (`BM25Okapi` in `rank_bm25`), fused using Reciprocal Rank Fusion (RRF) and re-ranked with a neural Cross-Encoder (`ms-marco-MiniLM-L-6-v2`). Synthesizes answers via Google Gemini API (with deterministic extractive fallback) enforcing strict in-text bounding-box coordinate provenance `[page, x, y, width, height]`.
2. **Pillar 2: Relational Knowledge Graph**: Mines scientific entities (`Paper`, `Author`, `Method`, `Dataset`, `Metric`) using `spaCy` NLP and models directed topologies with `NetworkX`. Serializes topologies into Cytoscape.js JSON, rendered via a force-directed layout (`cola`) with dynamic query-relevance scaling and path illumination.
3. **User Interface**: A split-screen research canvas (React + Vite + Tailwind CSS) with a persistent chat pane on the left and a tabbed right pane toggling between the Cytoscape graph canvas and the synchronized PDF.js document reader.
4. **DevOps & Verification**: Containerized via Docker Compose (`docker compose up --build`), validated through persistent `pytest` unit/integration test suites and automated GitHub Actions CI (`.github/workflows/ci.yml`).

---

## Technical Context

**Language/Version**: Python 3.10+ (Backend), JavaScript / React 18+ (Frontend)

**Primary Dependencies**:
- *Backend API*: `fastapi`, `uvicorn`, `pydantic>=2.0`, `python-multipart`
- *Document Parsing*: `pypdf`, `pdfplumber`
- *AI & Information Retrieval*: `sentence-transformers`, `chromadb`, `rank-bm25`, `spacy`, `networkx`, `google-generativeai`
- *Frontend Presentation*: `react`, `vite`, `tailwindcss`, `cytoscape`, `cytoscape-cola`, `pdfjs-dist`, `lucide-react`, `axios`
- *DevOps & Testing*: `docker`, `docker-compose`, `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`

**Storage**:
- *Vector Embeddings*: `ChromaDB` persistent client directory (`./data/chromadb`)
- *Relational Metadata*: `SQLite` relational database (`./data/sqlite/scholargraph.db`)
- *Document Repository*: Local filesystem storage (`./data/papers/`)

**Testing**: `pytest` unit, integration, and edge-case suites across all subsystems; automated GitHub Actions CI pipeline executing on every push and pull request.

**Target Platform**: Cross-platform (Windows, Linux, macOS), containerized via Docker Desktop / Docker Engine.

**Project Type**: Decoupled 4-Tier Web Application (Presentation, Application API, AI & Modeling, Persistence).

**Performance Goals**:
- Retrieval Latency: $< 2.0\text{ seconds}$
- End-to-End Synthesis Latency: $< 4.0\text{ seconds}$
- Retrieval Precision ($MRR@5$): $\ge 0.85$
- Graph Render Latency: $< 1.0\text{ second}$ for $\le 100$ nodes

**Constraints**:
- Zero-Hallucination Invariant: 0.0% ungrounded claims; every claim must carry pixel-level bounding-box coordinates `[page, x, y, width, height]`.
- Out-of-the-box local execution in $< 5\text{ minutes}$ with pre-packaged seed dataset (5–8 papers).
- Zero mandatory paid API keys (Gemini free tier supported; local extractive fallback guaranteed).

**Scale/Scope**: Multi-PDF collections (up to 20 concurrent papers per collection), seed dataset of 5-8 seminal AI papers.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-evaluated post Phase 1 design.*

| Constitutional Principle | Design & Architecture Compliance | Status |
| :--- | :--- | :---: |
| **I. Grounded Synthesis & Zero-Hallucination Invariant** | In-text citation tokens with bounding-box coordinates `[page, x, y, w, h]` required for all assertions; explicit "insufficient context" message returned if evidence is lacking. | **PASSED** |
| **II. Decoupled 4-Tier Architecture** | Strict separation: Tier 1 (React+Vite+Cytoscape+PDF.js), Tier 2 (FastAPI+Pydantic v2), Tier 3 (Sentence-Transformers+Cross-Encoder+spaCy+NetworkX), Tier 4 (ChromaDB+SQLite). | **PASSED** |
| **III. Hybrid Retrieval Supremacy** | Dual-pipeline retrieval (BM25 sparse + ChromaDB dense) merged via Reciprocal Rank Fusion (RRF, $k=60$) and re-ranked using neural Cross-Encoder (`ms-marco-MiniLM-L-6-v2`). | **PASSED** |
| **IV. Test-Driven Verification & Benchmark Gates** | Automated `pytest` unit/integration test suites for every subsystem; quantitative $MRR@5 \ge 0.85$ benchmark gate; automated GitHub Actions CI workflow on push. | **PASSED** |
| **V. Academic Reproducibility & Executability** | Single-command Docker Compose execution (`docker compose up --build`), bundled seed papers, and setup time $< 5\text{ minutes}$. | **PASSED** |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-core-research-platform/
├── spec.md              # Requirements specification & user stories
├── plan.md              # This technical implementation blueprint
├── research.md          # Phase 0 technology decisions & rationale
├── data-model.md        # Phase 1 SQLite schema, ChromaDB metadata & Pydantic models
├── quickstart.md        # Phase 1 run & validation guide
├── checklists/
│   └── requirements.md  # Spec quality validation checklist
└── contracts/
    └── rest-api.md      # OpenAPI REST contract specifications
```

### Source Code Layout (Repository Root)

```text
ScholarGraph/
├── .github/
│   └── workflows/
│       └── ci.yml                     # GitHub Actions CI workflow (pytest, lint, benchmark)
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── document_routes.py         # POST /upload, GET /documents, GET /pdf
│   │   ├── query_routes.py            # POST /query (Hybrid RAG + Synthesis)
│   │   ├── graph_routes.py            # GET /graph, POST /graph/highlight
│   │   └── benchmark_routes.py        # GET /benchmarks/run
│   ├── benchmarks/
│   │   ├── __init__.py
│   │   ├── benchmark_data.json        # 25 standardized evaluation questions + ground truth
│   │   └── evaluate_rag.py            # CLI benchmark evaluation harness (MRR@5 & MAP@5)
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── entity_miner.py            # spaCy NER + regex scientific entity extractor
│   │   └── graph_builder.py           # NetworkX DiGraph builder & Cytoscape serializer
│   ├── models/
│   │   ├── __init__.py
│   │   ├── paper.py                   # PaperMetadata, BoundingBox, IngestionStatus
│   │   ├── rag.py                     # QueryRequest, QueryResponse, CitationToken
│   │   ├── graph.py                   # CytoscapeNode, CytoscapeEdge, GraphResponse
│   │   └── benchmark.py               # BenchmarkQueryEvaluation, BenchmarkSummary
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── pdf_parser.py              # pdfplumber + pypdf section chunker & coordinate extractor
│   │   └── text_cleaner.py            # Text normalization & character encoding preservation
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── bm25_index.py              # rank_bm25 sparse keyword index
│   │   ├── vector_store.py            # ChromaDB dense client & sentence-transformers embedding
│   │   ├── reranker.py                # Reciprocal Rank Fusion (RRF) & Cross-Encoder re-ranker
│   │   └── generator.py               # Gemini API client + local deterministic extractive fallback
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db.py                      # SQLite connection, migrations, paper metadata repository
│   │   └── file_store.py              # Local PDF storage manager
│   ├── Dockerfile                     # Python 3.10-slim backend container
│   ├── requirements.txt               # Backend dependencies
│   └── main.py                        # FastAPI application entrypoint & healthcheck
├── frontend/
│   ├── public/
│   │   └── vite.svg
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWorkspace.jsx      # Left panel: Q&A chat, prompt input, citation badges
│   │   │   ├── GraphCanvas.jsx        # Right panel tab 1: Interactive Cytoscape.js canvas
│   │   │   ├── PDFViewer.jsx          # Right panel tab 2: Synchronized PDF.js reader + highlights
│   │   │   ├── UploadModal.jsx        # Multi-PDF upload modal with staged progress indicators
│   │   │   └── Header.jsx             # Top bar: Paper selector, API key settings, system status
│   │   ├── services/
│   │   │   └── api.js                 # Axios API client wrapper
│   │   ├── App.jsx                    # Root split-screen layout component
│   │   ├── main.jsx                   # React DOM entrypoint
│   │   └── index.css                  # Tailwind CSS styling
│   ├── Dockerfile                     # Node/Vite or Nginx frontend container
│   ├── package.json                   # Frontend dependencies
│   └── tailwind.config.js             # Tailwind design configuration
├── data/
│   ├── chromadb/                      # Persistent ChromaDB vector collections (gitignored)
│   ├── sqlite/                        # Persistent SQLite database (gitignored)
│   └── papers/                        # Seed papers and uploaded PDF storage
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures, mock Gemini API, test database
│   ├── test_parsers.py                # PDF parser & bounding-box coordinate unit tests
│   ├── test_rag.py                    # BM25, ChromaDB, RRF, and Cross-Encoder unit tests
│   ├── test_graph.py                  # spaCy entity mining & NetworkX topology tests
│   ├── test_api.py                    # FastAPI endpoint integration tests
│   └── test_benchmarks.py             # Automated MRR@5 retrieval precision benchmark test
├── docker-compose.yml                 # Multi-container orchestration (backend + frontend)
├── .env.example                       # Template environment configuration
└── README.md                          # Root setup, architecture, and execution guide
```

---

## Complexity Tracking

*No constitutional violations identified. Design adheres strictly to the 4-tier decoupled architecture, zero-hallucination invariant, and hybrid retrieval supremacy.*

| Component Choice | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Hybrid RAG (BM25 + Dense + Cross-Encoder)** | Scientific papers contain exact formulas and acronyms that dense search misses. | Dense-only search drops MRR@5 below the required 0.85 threshold. |
| **In-Memory NetworkX Graph vs. Neo4j** | In-memory graph is lightweight, fast, and serializes directly to Cytoscape.js JSON. | Neo4j requires a dedicated JVM container requiring $>2\text{GB}$ RAM, conflicting with 5-minute setup. |
| **Dual Gemini + Extractive Fallback** | Ensures fluent synthesis when configured while guaranteeing zero-crash local execution without an API key. | Single-provider cloud LLM causes evaluation failure if evaluator has no API key; local 7B SLM exceeds consumer CPU limits. |
