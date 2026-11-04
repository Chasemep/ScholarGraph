# ScholarGraph

A dual-engine platform combining hybrid Retrieval-Augmented Generation (RAG) with interactive knowledge graphs for grounded, verifiable scientific literature synthesis.

---

## 1. Overview & Problem Addressed

Scientific literature grows by millions of publications annually. Researchers and software engineers face two persistent workflow friction points:
1. **Isolated Document Silos**: Standard keyword searches across lengthy PDFs return isolated fragments without conceptual lineage, method dependencies, or cross-paper synthesis.
2. **Generative Model Hallucinations**: Standard language model interfaces frequently invent citations, misattribute results, or distort empirical numbers without traceable page coordinates.

ScholarGraph addresses both challenges with a coupled dual-engine architecture:
- **Verifiable Hybrid Synthesis Engine**: Ingests scientific PDFs, extracts structured spatial chunks with bounding-box coordinates, indexes dense (ChromaDB) and sparse (BM25) representations, fuses candidates via Reciprocal Rank Fusion ($k=60$), applies neural cross-encoder re-ranking (`ms-marco-MiniLM-L-6-v2`), and produces syntheses with precise, clickable citations that directly highlight original source passages.
- **Scientific Entity & Lineage Graph Engine**: Mines key concepts, methods, authors, and datasets to construct an interactive Cytoscape.js knowledge graph, allowing users to explore conceptual relationships, dependencies, and citation lineages.

---

## 2. Core Capabilities

- **Spatial Bounding-Box Grounding**: Every inline citation badge (`[paper_vaswani2017, Page 4]`) links directly to the embedded PDF reader, scrolling to the exact page and rendering coordinate-accurate highlight overlays on source evidence.
- **Hybrid Retrieval & Neural Re-Ranking**: Combines BM25 lexical search with 384-dimensional dense embeddings (`all-MiniLM-L6-v2`), candidate reciprocal rank fusion, and neural cross-encoder re-scoring.
- **Defensive Grounding & Offline Mode**: Out-of-corpus queries automatically return structured refusal notices with actionable clarification suggestions. When generative cloud APIs are offline or unconfigured, a deterministic extractive fallback synthesizer returns direct verbatim passages from the indexed corpus.
- **Interactive Knowledge Graph Canvas**: Visualizes papers, concepts, and relationships with custom force-directed layouts, timeline ordination, neighborhood filtering, and inspectable node detail drawers.
- **Dynamic Corpus Management**: Ingests scientific papers with background parsing, text normalization, and vectorized indexing.

---

## 3. Architecture & Repository Structure

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION TIER (FRONTEND)                    │
│   React 18 · Vite 5 · Tailwind CSS · Cytoscape.js · PDF.js Canvas      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST / JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                       APPLICATION API TIER (BACKEND)                   │
│         FastAPI · Pydantic v2 · Async Ingestion Background Tasks       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Pipeline Orchestration
┌───────────────────────────────────▼────────────────────────────────────┐
│                    RETRIEVAL, RE-RANKING & GRAPH ENGINE                │
│ pdfplumber · rank-bm25 · sentence-transformers · Cross-Encoder · spaCy │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Persistence Layer
┌───────────────────────────────────▼────────────────────────────────────┐
│                         DATA & PERSISTENCE TIER                        │
│   ChromaDB (Dense Vectors) · SQLite (Catalog) · Local Paper Store      │
└────────────────────────────────────────────────────────────────────────┘
```

### Directory Layout

```text
ScholarGraph/
├── backend/                  # FastAPI Application & ML Pipelines
│   ├── api/                  # REST route controllers (query, documents, graph, benchmark)
│   ├── core/                 # Centralized prompts, constants & guardrail definitions
│   ├── graph/                # Entity mining, topic clustering & Cytoscape graph builders
│   ├── models/               # Pydantic schemas (paper, rag, graph)
│   ├── parsers/              # PDF coordinate extraction & text cleaning
│   ├── rag/                  # BM25 index, ChromaDB vector store, RRF reranker, synthesis generator
│   ├── scripts/              # Seed database & model caching utilities
│   └── storage/              # SQLite catalog & filesystem PDF store
├── frontend/                 # React 18 + Vite 5 User Interface
│   └── src/
│       ├── components/ui/    # Reusable atomic UI primitives (Button, Badge, Modal)
│       ├── features/
│       │   ├── corpus/       # PDF viewer with spatial highlights & upload drawer
│       │   ├── knowledge-graph/ # Cytoscape graph canvas, controls, legend & node drawer
│       │   └── synthesis/    # Query input, stream workspace, citation badges & math rendering
│       ├── services/         # API client & backend endpoints
│       └── utils/            # Citation parser & LaTeX math formatting
└── tests/                    # 68 Automated Test Suites (87.4% Line Coverage)
    ├── test_data/            # Bundled seed PDFs & real-paper test corpus
    └── test_e2e_playwright_suite.py # Multi-paper browser test with video recording
```

| Layer | Component Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite 5, Tailwind CSS, Cytoscape.js (`cola` layout), Mozilla `pdfjs-dist`, Lucide React |
| **Backend API** | Python 3.10+, FastAPI, Uvicorn, Pydantic v2, HTTPX |
| **Information Retrieval & ML** | `pdfplumber`, `pypdf`, `rank-bm25`, `sentence-transformers` (`all-MiniLM-L6-v2`), `cross-encoder/ms-marco-MiniLM-L-6-v2`, `spaCy` |
| **Storage & Persistence** | ChromaDB (`PersistentClient`), SQLite 3, filesystem PDF archive |
| **Tooling & Orchestration** | Docker, Docker Compose, Pytest, Playwright, GitHub Actions CI |

---

## 4. Getting Started

### Option A: Run via Docker Compose (Recommended)

Ensure [Docker Desktop](https://www.docker.com/products/docker-desktop/) is installed and running.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Chasemep/ScholarGraph.git
   cd ScholarGraph
   ```

2. **Configure environment (Optional):**
   ```bash
   cp .env.example .env
   # Add GEMINI_API_KEY if Google Gemini generative synthesis is desired;
   # otherwise ScholarGraph will run in deterministic extractive fallback mode.
   ```

3. **Start the application stack:**
   ```bash
   docker compose up --build
   ```

4. **Access services:**
   - Web Application: [http://localhost:3000](http://localhost:3000)
   - FastAPI Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Health Status: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Option B: Local Native Setup

#### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

#### 1. Backend Service
```bash
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

pip install --upgrade pip
pip install -r backend/requirements.txt
python -m backend.scripts.download_models

uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

#### 2. Frontend Client
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

The frontend client will be accessible at [http://localhost:5173](http://localhost:5173) (or [http://localhost:3000](http://localhost:3000) when served via production Nginx).

---

## 5. Automated Verification & Test Execution

ScholarGraph enforces rigorous automated quality gates across unit, integration, API contract, and end-to-end browser workflows:

- **68 Automated Backend Tests** with **87.4% line coverage** (target $\ge 80\%$).
- **Deterministic Zero-Hallucination Guardrails** validating refusal responses and citation accuracy.
- **Playwright Browser E2E Suite** testing multi-paper PDF ingestion and cross-paper synthesis with automated WebM video recording.

### Running Backend Tests
```bash
# Execute unit and integration tests with coverage tracking
pytest --cov=backend --cov-report=term-missing
```

### Running All Tests (Unit + Integration + E2E)
```bash
# Unified cross-platform test runner
python run_all_tests.py
```
*(On Windows PowerShell, `./run_all_tests.ps1` can also be used).*

All automated test targets are validated in continuous integration via [`.github/workflows/ci.yml`](./.github/workflows/ci.yml).
