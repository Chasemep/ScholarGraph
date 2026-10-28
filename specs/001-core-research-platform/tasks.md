---
description: "Task list for Core Grounded Literature Research Platform implementation"
---

# Tasks: Core Grounded Literature Research Platform

**Input**: Design documents from `specs/001-core-research-platform/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/rest-api.md`, `quickstart.md`)  
**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `data-model.md`, `contracts/rest-api.md`, `research.md`, `quickstart.md`  
**Constitution**: Strict adherence to Decoupled 4-Tier Architecture, Zero-Hallucination Invariant, Hybrid Retrieval Supremacy, and Continuous Automated Testing.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project directory initialization, dependency manifests, model caching, and configuration.

- [x] T001 Initialize repository directory structure (`backend/`, `frontend/`, `tests/`, `data/papers/`, `data/chromadb/`, `data/sqlite/`) per `plan.md`
- [x] T002 [P] Configure backend Python dependencies (`fastapi`, `uvicorn`, `pydantic>=2.0`, `pypdf`, `pdfplumber`, `sentence-transformers`, `chromadb`, `rank-bm25`, `spacy`, `networkx`, `google-generativeai`, `pytest`, `pytest-cov`, `httpx`) in `backend/requirements.txt`
- [x] T003 [P] Initialize frontend React + Vite + Tailwind CSS project configuration with UI libraries (`cytoscape`, `cytoscape-cola`, `pdfjs-dist`, `lucide-react`, `axios`) in `frontend/package.json` and `frontend/tailwind.config.js`
- [x] T004 [P] Create model pre-caching script to download `en_core_web_sm` and pre-warm HuggingFace models (`all-MiniLM-L6-v2`, `ms-marco-MiniLM-L-6-v2`) in `backend/scripts/download_models.py`
- [x] T005 Create centralized application configuration with Pydantic `BaseSettings` loading `GEMINI_API_KEY`, server ports, and storage paths in `backend/config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data layer, database persistence, and API routing infrastructure that MUST be complete before ANY user story can execute.

- [x] T006 [P] Implement Pydantic v2 core document and bounding-box data models (`BoundingBox`, `PaperMetadata`, `TextChunk`) with coordinate constraints `[page, x, y, width, height]` in `backend/models/paper.py`
- [x] T007 [P] Implement SQLite database connection manager, table creation migrations (`papers`, `paper_chunks`), and metadata repository methods in `backend/storage/db.py`
- [x] T008 [P] Implement local PDF file storage repository manager for persisting and serving binary document files in `backend/storage/file_store.py`
- [x] T009 [P] Initialize ChromaDB persistent client, collection setup (`scholar_chunks`), and 384-d dense embedding wrapper in `backend/rag/vector_store.py`
- [x] T010 Create FastAPI application entrypoint, CORS middleware, global exception handlers, and readiness healthcheck endpoint `GET /api/health` in `backend/main.py`
- [x] T011 Bundle seed collection of 5 high-impact open-access papers (*Attention Is All You Need, LoRA, BERT, RoFormer, FlashAttention*) into `data/papers/`

**Checkpoint**: Core persistence and application foundation ready — User Story implementation can proceed.

---

## Phase 3: User Story 1 - Multi-Document Comparative Q&A with Click-to-Verify Provenance (Priority: P1) 🎯 MVP

**Goal**: Enable users to pose comparative queries across papers and receive strictly factual answers where every claim links to a clickable citation token that jumps to the exact page and paints a luminous bounding-box highlight over the source paragraph.

**Independent Test**: Ingest two seed papers (*Attention Is All You Need* and *LoRA*), submit a comparative question regarding parameter efficiency, verify that the response cites both papers accurately with non-null coordinates, click a citation token, and confirm the PDF viewer jumps to the exact page and renders the highlight overlay.

### Tests for User Story 1
- [ ] T012 [P] [US1] Create automated unit and contract tests for BM25 indexing, ChromaDB vector retrieval, RRF fusion, and Cross-Encoder re-ranking in `tests/test_rag.py`
- [ ] T013 [P] [US1] Create automated integration tests for grounded citation verification and 0.0% hallucination fallback in `tests/test_synthesis.py`

### Implementation for User Story 1
- [ ] T014 [P] [US1] Create Pydantic v2 RAG request and response models (`QueryRequest`, `QueryResponse`, `CitationToken`) with score validations in `backend/models/rag.py`
- [ ] T015 [P] [US1] Implement sparse lexical keyword index with tokenization and domain stopword filtering using `rank_bm25.BM25Okapi` in `backend/rag/bm25_index.py`
- [ ] T016 [US1] Implement candidate fusion using Reciprocal Rank Fusion ($k=60$) and neural cross-attention re-ranking (`ms-marco-MiniLM-L-6-v2`) returning Top-5 passages in `backend/rag/reranker.py`
- [ ] T017 [US1] Implement strict context-constrained synthesis generator supporting Google Gemini API with automatic fallback to deterministic extractive synthesis in `backend/rag/generator.py`
- [ ] T018 [US1] Implement RAG query endpoint `POST /api/query` and PDF stream endpoint `GET /api/documents/{paper_id}/pdf` in `backend/api/query_routes.py`
- [ ] T019 [P] [US1] Implement frontend Axios API client wrapper with request/response interceptors in `frontend/src/services/api.js`
- [ ] T020 [US1] Build left-panel chat workspace component with prompt input, markdown rendering, and clickable citation badges in `frontend/src/components/ChatWorkspace.jsx`
- [ ] T021 [US1] Build right-panel synchronized PDF viewer using `pdfjs-dist` supporting smooth page jump and luminous bounding-box highlight overlay rendering in `frontend/src/components/PDFViewer.jsx`
- [ ] T022 [US1] Integrate split-screen workspace in `frontend/src/App.jsx`, wiring citation click events in `ChatWorkspace.jsx` to scroll and highlight actions in `PDFViewer.jsx`

**Checkpoint**: User Story 1 is fully functional and delivers an independently testable MVP.

---

## Phase 4: User Story 2 - Visual Knowledge Graph & Concept Lineage Exploration (Priority: P2)

**Goal**: Deliver an interactive 2D Cytoscape.js network canvas mapping papers, authors, methods, datasets, and metrics with dynamic prompt-activated relevance scaling and path illumination.

**Independent Test**: Load the graph view for ingested papers, verify color- and shape-coded entity nodes, submit a search prompt, and confirm that relevant nodes scale up while unrelated nodes dim to 20% opacity.

### Tests for User Story 2
- [ ] T023 [P] [US2] Create unit tests for spaCy scientific entity extraction patterns and NetworkX graph serialization in `tests/test_graph.py`

### Implementation for User Story 2
- [ ] T024 [P] [US2] Create Cytoscape-compliant graph serialization schemas (`CytoscapeNode`, `CytoscapeEdge`, `GraphResponse`) in `backend/models/graph.py`
- [ ] T025 [P] [US2] Implement scientific entity extraction pipeline (`Paper`, `Author`, `Method`, `Dataset`, `Metric`) using `spaCy` (`en_core_web_sm`) and pattern matchers in `backend/graph/entity_miner.py`
- [ ] T026 [US2] Implement `NetworkX` directed graph topology builder with typed relationships (`AUTHORED`, `PROPOSES`, `EVALUATES_ON`, `CITES`, `ACHIEVES`) and Cytoscape serialization in `backend/graph/graph_builder.py`
- [ ] T027 [US2] Implement graph API endpoints `GET /api/graph` and `POST /api/graph/highlight` in `backend/api/graph_routes.py`
- [ ] T028 [US2] Build interactive 2D Cytoscape canvas component with `cola` force-directed physics layout, multi-shape entity styling, and zoom/pan controls in `frontend/src/components/GraphCanvas.jsx`
- [ ] T029 [US2] Implement prompt-activated relevance dynamics in `frontend/src/components/GraphCanvas.jsx`: scale matching nodes by score, thicken active relational paths to 4px with luminous glow, and dim peripheral nodes to 20% opacity
- [ ] T030 [US2] Integrate tabbed right-panel toggle between Graph Canvas and PDF Reader in `frontend/src/App.jsx`, auto-switching to PDF Reader upon citation click

**Checkpoint**: User Stories 1 and 2 work seamlessly together in the split-screen research canvas.

---

## Phase 5: User Story 5 - Continuous Automated Testing & GitHub Actions CI Gate (Priority: P2)

**Goal**: Ensure every major component is accompanied by automated unit and edge-case tests, validated continuously on GitHub via GitHub Actions CI on every push and pull request.

**Independent Test**: Push a commit or pull request to GitHub, verify that the GitHub Actions CI workflow triggers automatically, executes all pytest suites in clean virtualization, and generates coverage reports.

### Implementation for User Story 5
- [ ] T031 [P] [US5] Implement pytest test fixtures, mock Gemini API responses, and isolated in-memory test databases in `tests/conftest.py`
- [ ] T032 [P] [US5] Implement comprehensive FastAPI endpoint integration tests (`/api/health`, `/api/query`, `/api/graph`, `/api/documents`) in `tests/test_api.py`
- [ ] T033 [US5] Create GitHub Actions CI workflow configuration (`.github/workflows/ci.yml`) executing on push/PR with Python 3.10, dependency caching, model caching, pytest execution, and $\ge 80\%$ coverage gate
- [ ] T034 [US5] Implement CI test report summary generation and badge output in `.github/workflows/ci.yml`

**Checkpoint**: Continuous integration gate protects the repository against regressions across all subsequent phases.

---

## Phase 6: User Story 3 - Section-Aware Document Ingestion & Spatial Coordinate Tracking (Priority: P3)

**Goal**: Provide a multi-PDF upload interface with asynchronous background task processing and spatial bounding-box extraction for runtime user documents.

**Independent Test**: Upload a fresh PDF paper via the UI dropzone, observe staged progress status badges (`Uploading` $\rightarrow$ `Parsing` $\rightarrow$ `Embedding` $\rightarrow$ `Ready`), and verify the new paper immediately appears in the document list, search index, and knowledge graph.

### Tests for User Story 3
- [ ] T035 [P] [US3] Create automated parser unit tests validating two-column extraction, section boundary categorization, Greek symbol preservation, and bounding-box accuracy in `tests/test_parsers.py`

### Implementation for User Story 3
- [ ] T036 [P] [US3] Create document ingestion task status models (`IngestionStatus`) in `backend/models/paper.py`
- [ ] T037 [US3] Implement hierarchical PDF parser and section-aware chunker using `pdfplumber` and `pypdf`, capturing normalized paragraph coordinates `[page, x, y, width, height]` in `backend/parsers/pdf_parser.py`
- [ ] T038 [P] [US3] Implement text cleaner and encoding normalization preserving mathematical notation and subscripts in `backend/parsers/text_cleaner.py`
- [ ] T039 [US3] Implement asynchronous background ingestion pipeline (parsing, embedding, BM25 indexing, graph node insertion) with staged status tracking in `backend/api/document_routes.py`
- [ ] T040 [US3] Build multi-PDF drag-and-drop upload modal with staged progress indicators (`Uploading`, `Parsing`, `Embedding`, `Ready`) in `frontend/src/components/UploadModal.jsx`
- [ ] T041 [US3] Build document selector dropdown and collection management header in `frontend/src/components/Header.jsx`

**Checkpoint**: Dynamic multi-PDF upload and asynchronous ingestion complete.

---

## Phase 7: User Story 4 - One-Command Containerized Deployment (Priority: P4)

**Goal**: Deliver a frictionless Docker Compose deployment allowing any evaluator to clone the repository and launch the full operational application in $< 5\text{ minutes}$ with zero host dependency issues.

**Independent Test**: Execute `docker compose up --build` on a clean system, confirm both services start healthy, and verify immediate availability of seed papers, Q&A synthesis, and knowledge graph.

### Implementation for User Story 4
- [ ] T042 [P] [US4] Create multi-stage backend `Dockerfile` based on `python:3.10-slim` with model caching and healthcheck probe in `backend/Dockerfile`
- [ ] T043 [P] [US4] Create frontend `Dockerfile` using multi-stage build (Node 18 build $\rightarrow$ Nginx lightweight runtime with `/api` reverse proxy) in `frontend/Dockerfile`
- [ ] T044 [US4] Create `docker-compose.yml` orchestrating `backend` and `frontend` services with persistent volume bindings (`./data/chromadb`, `./data/sqlite`, `./data/papers`) and healthcheck dependencies
- [ ] T045 [US4] Create seed database initialization script to automatically index bundled seed papers on container first boot in `backend/scripts/seed_database.py`
- [ ] T046 [US4] Perform end-to-end container startup verification following `quickstart.md` ensuring clean-boot availability in $< 5\text{ minutes}$

**Checkpoint**: Application is fully containerized and reproducible out of the box.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Quantitative IR benchmark verification, UI settings polish, report artifact generation, and final documentation.

- [ ] T047 [P] Create standardized 25-question IR evaluation dataset and CLI benchmark harness verifying $MRR@5 \ge 0.85$ and formatting output tables for Chapter 5 of the technical report in `backend/benchmarks/evaluate_rag.py`
- [ ] T048 [P] Implement benchmark route `GET /api/benchmarks/run` in `backend/api/benchmark_routes.py` and automated verification test in `tests/test_benchmarks.py`
- [ ] T049 [P] Build Settings / API Key modal allowing users to enter a custom Gemini API key or switch to local fallback in `frontend/src/components/Header.jsx`
- [ ] T050 Polish UI error handling, toast notifications, and loading skeletons in `frontend/src/App.jsx`
- [ ] T051 Write comprehensive root `README.md` documenting problem description, 4-tier architecture, prerequisites, PowerShell and Docker setup, seed paper walkthrough, and UI screenshots per Course Guidelines §3.2

---

## Dependencies & Execution Order

### Phase Dependencies
```
Phase 1: Setup 
     │
     ▼
Phase 2: Foundational (BLOCKS all User Stories)
     │
     ├───────────────────────┬───────────────────────┐
     ▼                       ▼                       ▼
Phase 3: US1 (P1) MVP    Phase 4: US2 (P2) Graph   Phase 5: US5 (P2) CI/CD
     │                       │                       │
     └───────────────────────┼───────────────────────┘
                             ▼
                 Phase 6: US3 (P3) Ingestion
                             │
                             ▼
                 Phase 7: US4 (P4) Docker
                             │
                             ▼
                 Phase 8: Polish & Report Align
```

### User Story Dependencies
- **User Story 1 (P1 - MVP)**: Can start immediately after Phase 2 (Foundational). Uses pre-bundled seed papers.
- **User Story 2 (P2 - Graph)**: Can start after Phase 2. Integrates with US1 for prompt-activated relevance highlighting.
- **User Story 5 (P2 - CI/CD)**: Can start after Phase 2. Establishes the automated GitHub Actions verification harness.
- **User Story 3 (P3 - Ingestion)**: Expands ingestion from static seed papers to dynamic multi-PDF user uploads.
- **User Story 4 (P4 - Docker)**: Packages all implemented backend and frontend services into container images.
- **Phase 8 (Polish)**: Executes benchmark harness and produces report tables.

---

## Parallel Execution Opportunities

```bash
# Foundational Parallel Block (Phase 2):
Task: "T006 Core Pydantic document models in backend/models/paper.py"
Task: "T007 SQLite database manager in backend/storage/db.py"
Task: "T008 Local PDF file store manager in backend/storage/file_store.py"
Task: "T009 ChromaDB persistent client in backend/rag/vector_store.py"

# User Story 1 Parallel Block (Phase 3):
Task: "T012 Unit tests in tests/test_rag.py"
Task: "T014 RAG request/response schemas in backend/models/rag.py"
Task: "T015 BM25 keyword index in backend/rag/bm25_index.py"
Task: "T019 Frontend Axios client in frontend/src/services/api.js"

# Containerization Parallel Block (Phase 7):
Task: "T042 Backend Dockerfile in backend/Dockerfile"
Task: "T043 Frontend Dockerfile in frontend/Dockerfile"
```

---

## Implementation Strategy: MVP First

1. **Step 1**: Complete **Phase 1 (Setup)** and **Phase 2 (Foundational)**.
2. **Step 2**: Implement **Phase 3 (User Story 1)**.  
   *Checkpoint*: You now have a working, independently testable MVP capable of answering comparative research questions across pre-loaded papers with synchronized bounding-box highlight proof in PDF.js.
3. **Step 3**: Implement **Phase 4 (User Story 2)**. Adds interactive 2D Cytoscape knowledge graph exploration and query-activated path highlighting.
4. **Step 4**: Implement **Phase 5 (User Story 5)**. Enforces GitHub Actions CI regression testing on every push.
5. **Step 5**: Implement **Phase 6 (User Story 3)** and **Phase 7 (User Story 4)**. Delivers runtime multi-PDF ingestion and one-command Docker Compose deployment.
6. **Step 6**: Execute **Phase 8 (Polish)**. Runs the 25-question $MRR@5$ benchmark harness and produces the test results matrix for Chapter 5 of your $\ge 20$-page technical report.

