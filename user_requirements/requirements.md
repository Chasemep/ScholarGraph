# ScholarGraph: Software Requirements Specification (SRS)

> **Document Version:** 1.0.0  
> **Course:** Software Design I  
> **Student:** Chase Pluimer  
> **Project:** ScholarGraph — Hybrid RAG & Knowledge Graph Platform for Scientific Literature  
> **Primary References:** Course Project Submission Guidelines (PDF), ScholarGraph Project Proposal (PPTX), User Stories (`academic_researcher.txt`, `industry_rd_engineer.txt`, `undergraduate_stem_student.txt`), and Project Constitution (`.specify/memory/constitution.md`).

---

## 1. Executive Summary & Project Purpose

Modern scientific research is paralyzed by two compounding crises:
1. **Literature Overload & Document Silos:** Over 5 million scientific papers are published annually. Researchers, engineers, and students spend dozens of hours navigating disconnected 20+ page PDF documents, manually extracting baseline numbers, reconciling contradictory experimental setups, and chasing convoluted citation trails.
2. **Generative AI Hallucinations & Distrust:** General-purpose AI chatbots (e.g., ChatGPT, Claude) frequently invent citations, fabricate experimental metrics, transpose matrix dimensions, and blend claims across unrelated papers without verifiable provenance. Such ungrounded outputs are unacceptable for academic research and production engineering.

**ScholarGraph** solves this dilemma through a dual-engine architecture:
- **Pillar 1: Grounded Hybrid RAG Pipeline:** Combines sparse BM25 keyword matching with dense vector embeddings (ChromaDB), merged via Reciprocal Rank Fusion (RRF), re-ranked via a neural Cross-Encoder, and constrained by a zero-hallucination generation invariant with pixel-level bounding-box provenance.
- **Pillar 2: Relational Knowledge Graph:** Mines scientific entities (`Paper`, `Author`, `Method`, `Dataset`, `Metric`) using spaCy NLP and models topological lineage with NetworkX, visualized through an interactive 2D Cytoscape.js canvas.

This document formally specifies the functional, non-functional, architectural, and academic compliance requirements for ScholarGraph.

---

## 2. User Personas & Pain Point Synthesis

The requirements in this specification directly address the real-world frustrations identified across the three target user types defined in Slide 3 of the project proposal and elaborated in the user stories:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               USER CONCERNS & REQUIREMENTS MAPPING                     │
├─────────────────────────┬──────────────────────────────────┬───────────────────────────┤
│ User Type & Persona     │ Core Real-World Frustration      │ Addressed By Requirement  │
├─────────────────────────┼──────────────────────────────────┼───────────────────────────┤
│ **Academia**            │ • 30+ papers read manually       │ • Multi-paper Q&A (FR-4)  │
│ Doctoral Researcher /   │ • Lost citation provenance       │ • Clickable proof (FR-6)  │
│ Graduate Student        │ • Hallucinated fake citations    │ • Zero-hallucination (NFR-2)│
│                         │ • Opaque research lineage        │ • Citation graph (FR-5)   │
├─────────────────────────┼──────────────────────────────────┼───────────────────────────┤
│ **Industry R&D**        │ • Contradictory benchmark tables │ • Metric extraction (FR-1)│
│ Senior ML Engineer /    │ • Missing hardware context       │ • Section chunking (FR-1) │
│ R&D Practitioner        │ • Keyword search misses nuances  │ • Hybrid RAG + RRF (FR-2) │
│                         │ • High stakes for faulty metrics │ • Cross-Encoder (FR-3)    │
├─────────────────────────┼──────────────────────────────────┼───────────────────────────┤
│ **Education**           │ • Dense terminology barrier      │ • Concept graph (FR-5)    │
│ STEM Undergraduate      │ • Endless citation rabbit holes  │ • Entity lineage (FR-5)   │
│ Student                 │ • Distorted AI explanations      │ • Context-only LLM (FR-4) │
│                         │ • Disjointed scrolling in PDFs   │ • Split-screen UI (FR-6)  │
└─────────────────────────┴──────────────────────────────────┴───────────────────────────┘
```

---

## 3. Decoupled 4-Tier Architecture Specification

In strict compliance with **Constitution Principle II**, ScholarGraph enforces a 4-tier separation of concerns:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         TIER 1: PRESENTATION TIER (FRONTEND)                           │
│     React + Vite  │  Tailwind CSS  │  Cytoscape.js (Canvas)  │  PDF.js (Reader)        │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ REST / JSON (OpenAPI)
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                       TIER 2: APPLICATION API TIER (BACKEND)                           │
│       FastAPI (Async)  │  Pydantic v2 Schemas  │  PyPDF / pdfplumber Ingestion         │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Internal Pipeline
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                     TIER 3: AI & MODELING TIER (INTELLIGENCE)                          │
│ Sentence-Transformers │ Cross-Encoder │ spaCy NLP (NER) │ NetworkX │ LangChain Orch.   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Query & Storage
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                    TIER 4: DATA & PERSISTENCE TIER (STORAGE)                           │
│      ChromaDB (Vector)  │  SQLite (Relational Metadata)  │  Local Document Storage     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Functional Requirements (FR)

### FR-1: Document Ingestion, Section-Aware Parsing & Coordinate Extraction
- **FR-1.1 (Multi-PDF Upload):** The system MUST provide an endpoint and UI dropzone accepting multi-PDF uploads (up to 20 concurrent papers per collection).
- **FR-1.2 (Section-Aware Extraction):** The parser MUST segment incoming PDFs into logical sections (`Title`, `Authors`, `Abstract`, `Introduction`, `Methodology`, `Results`, `Discussion`, `References`, and `Tables/Appendices`).
- **FR-1.3 (Bounding-Box Coordinate Tracking):** The parser MUST capture spatial bounding-box coordinates for every extracted paragraph and table cell in the format `[page_number, x, y, width, height]`.
- **FR-1.4 (Relational Cataloging):** Extracted paper metadata (`id`, `title`, `authors`, `year`, `abstract`, `doi`, `filepath`) MUST be persisted in SQLite.
- **FR-1.5 (Character Encoding Integrity):** The parser MUST preserve mathematical notation, Greek symbols ($\alpha, \beta, \gamma$), and subscript/superscript tokens without text corruption.

### FR-2: Dual-Index Hybrid Search (BM25 + ChromaDB Dense Vector)
- **FR-2.1 (Dense Embedding Index):** The system MUST embed parsed text chunks using `sentence-transformers/all-MiniLM-L6-v2` and store 384-dimensional dense vectors in ChromaDB alongside chunk metadata (`paper_id`, `section`, `page`, `bbox`).
- **FR-2.2 (Sparse BM25 Index):** The system MUST tokenize and maintain an in-memory sparse keyword index using `rank_bm25` over all ingested chunks to ensure exact matching of model names, acronyms, author surnames, and formulas.
- **FR-2.3 (Dual Candidate Retrieval):** Every search query MUST simultaneously retrieve the top $K=20$ candidates from the ChromaDB dense index and the top $K=20$ candidates from the BM25 index.
- **FR-2.4 (Reciprocal Rank Fusion):** The engine MUST fuse candidate lists using the reciprocal rank formula:
  $$RRF(d) = \sum_{m \in \{\text{Dense}, \text{BM25}\}} \frac{1}{60 + r_m(d)}$$
  producing a unified, deduplicated list of candidate passages.

### FR-3: Cross-Encoder Neural Re-Ranking
- **FR-3.1 (Cross-Attention Scoring):** The system MUST feed candidate passage pairs `(query, passage_text)` through a pre-trained neural Cross-Encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
- **FR-3.2 (Top-5 Filtration):** The re-ranker MUST sort candidates by raw cross-attention relevance score and extract the top $K=5$ most salient passages for context injection.
- **FR-3.3 (Score Normalization):** Relevance scores MUST be normalized to $[0.0, 1.0]$ and returned in API responses for verification.

### FR-4: Grounded Synthesis & Zero-Hallucination Guardrails
- **FR-4.1 (Strict Context Prompting):** The LLM prompt MUST enforce an absolute context boundary: *"Answer ONLY using the provided context passages. Every claim must carry a bracketed citation token [PaperID, Page X]. If context is missing or ambiguous, you MUST explicitly state that the literature does not contain the answer."*
- **FR-4.2 (Zero Generative Speculation):** If the Top-5 retrieved passages do not contain sufficient evidence to answer the query, the system MUST return a deterministic status: `{"status": "insufficient_context", "message": "The ingested literature does not contain sufficient evidence to answer this query."}`.
- **FR-4.3 (Deterministic Citation Tokens):** Every synthesized claim MUST include clickable citation tokens linked to the metadata record: `{ paper_id, title, page, bbox: [page, x, y, w, h] }`.
- **FR-4.4 (Multi-Paper Comparative Synthesis):** The engine MUST support multi-document synthesis queries (e.g., comparing runtime, parameter counts, or benchmark scores between Paper A and Paper B).

### FR-5: Automated Scientific Entity Mining & Interactive Knowledge Graph
- **FR-5.1 (Scientific NER Mining):** The backend MUST process ingested text using spaCy (`en_core_web_sm`) augmented with domain regex matchers to mine five entity types:
  - `Paper` (Document entity)
  - `Author` (Researcher/Creator)
  - `Method` (Model, Algorithm, Architecture)
  - `Dataset` (Evaluation Benchmark)
  - `Metric` (Score, Measurement Unit, Quantitative Result)
- **FR-5.2 (Typed Relational Modeling):** The system MUST construct a directed graph in `NetworkX` with typed edges:
  - `(Author)-[:AUTHORED]->(Paper)`
  - `(Paper)-[:PROPOSES]->(Method)`
  - `(Paper)-[:EVALUATES_ON]->(Dataset)`
  - `(Paper)-[:CITES]->(Paper)`
  - `(Method)-[:ACHIEVES]->(Metric)`
- **FR-5.3 (Cytoscape Serialization):** The backend MUST expose a GET `/api/graph` endpoint returning Cytoscape-compliant JSON: `{ elements: { nodes: [...], edges: [...] } }`.
- **FR-5.4 (Interactive 2D Graph Canvas):** The frontend MUST render the graph with Cytoscape.js featuring force-directed layout, category color coding, zoom/pan controls, search filtering, and click-to-highlight neighborhood expansion.

### FR-6: Split-Screen Research Canvas & Synchronized PDF Viewer
- **FR-6.1 (Dual-Pane Workspace):** The UI MUST provide a responsive split-screen layout:
  - **Left Pane:** Query input, multi-document synthesis output, entity filters, and citation badges.
  - **Right Pane:** Embedded high-fidelity PDF reader powered by `PDF.js`.
- **FR-6.2 (Synchronized Citation Jump):** Clicking any citation token in the synthesis text MUST instruct the PDF viewer to scroll smoothly to the exact target page.
- **FR-6.3 (Luminous Bounding-Box Highlighting):** Upon jumping, the viewer MUST paint a luminous, translucent highlight overlay directly over the bounding-box coordinates `[x, y, w, h]` corresponding to the cited paragraph.
- **FR-6.4 (Graph Modal / Drawer):** The UI MUST allow users to toggle between the PDF viewer and the interactive knowledge graph canvas without losing query state.

---

## 5. Non-Functional Requirements (NFR)

### NFR-1: Performance & Latency Benchmarks
- **NFR-1.1 (Retrieval Precision):** The hybrid retrieval pipeline MUST achieve a Mean Reciprocal Rank at 5 ($MRR@5$) $\ge 0.85$ on the standardized test question suite.
- **NFR-1.2 (Retrieval Latency):** Hybrid retrieval (BM25 + ChromaDB + Cross-Encoder re-ranking) MUST complete in $< 2.0\text{ seconds}$ for a collection of up to 20 papers.
- **NFR-1.3 (Synthesis Latency):** Full end-to-end query synthesis MUST complete in $< 4.0\text{ seconds}$ on standard consumer hardware.
- **NFR-1.4 (Graph Render Latency):** The interactive Cytoscape canvas MUST render and achieve layout convergence in $< 1.0\text{ second}$ for graphs containing $\le 100$ nodes and $\le 250$ edges.

### NFR-2: Grounded Accuracy & Zero-Hallucination Invariant
- **NFR-2.1 (Hallucination Rate):** The system MUST maintain a $0.0\%$ ungrounded assertion rate. Every sentence in the synthesis output must be verifiable against an extracted passage.
- **NFR-2.2 (Bounding Coordinate Fidelity):** $100\%$ of generated citation tokens must point to valid, non-null page coordinates within the ingested document corpus.

### NFR-3: Usability & User Experience
- **NFR-3.1 (Zero Friction Reading):** Users must be able to verify any synthesized claim in less than 2 clicks (1 click on citation token $\rightarrow$ immediate jump and highlight).
- **NFR-3.2 (Visual Hierarchy):** Entity types on the graph canvas MUST use distinct, accessible color palettes:
  - Papers: Blue (`#2563EB`)
  - Methods: Emerald (`#059669`)
  - Datasets: Amber (`#D97706`)
  - Authors: Purple (`#7C3AED`)
  - Metrics: Rose (`#E11D48`)

### NFR-4: Modularity, Extensibility & Type Safety
- **NFR-4.1 (Pydantic v2 Contracts):** All API request and response models MUST be strictly defined using Pydantic v2 schemas (`backend/models/`).
- **NFR-4.2 (OpenAPI Specification):** FastAPI MUST automatically generate interactive Swagger documentation accessible at `/docs`.
- **NFR-4.3 (Decoupled Persistence):** Storage backends (ChromaDB, SQLite, Local File Store) must be isolated behind repository interfaces to allow swapping or upgrading without altering business logic.

### NFR-5: Academic Reproducibility & Out-of-the-Box Execution
- **NFR-5.1 (No Proprietary API Keys Required):** The core retrieval, re-ranking, NER, and graph visualization pipelines MUST operate entirely using local, open-source models (`all-MiniLM-L6-v2`, `ms-marco-MiniLM-L-6-v2`, `en_core_web_sm`).
- **NFR-5.2 (Bundled Seed Dataset):** The repository MUST include a pre-packaged seed dataset of 5–8 seminal open-access AI/ML papers (e.g., Attention Is All You Need, LoRA, BERT, RoFormer) so evaluators can run the full system immediately without manual downloads.
- **NFR-5.3 (Fast Setup Time):** An evaluator following the `README.md` instructions must be able to clone, install, and execute the complete system in $< 5\text{ minutes}$.
- **NFR-5.4 (Complete Docker Compose Orchestration):** The entire application (presentation UI, application API backend, AI models, and persistent storage volumes) MUST be containerized and runnable via a single command:
  ```bash
  docker compose up --build
  ```
  - The `docker-compose.yml` specification MUST define:
    1. A `backend` service building from a Python 3.10+ `Dockerfile`, pre-caching required HuggingFace embeddings and spaCy linguistic models, exposing port `8000`, and configuring a healthcheck probe on `GET /api/health`.
    2. A `frontend` service building from a Node/Vite (or Nginx production) `Dockerfile`, proxying API calls to the backend, and exposing port `5173` (or `80`).
    3. Persistent named volumes or host-mounted directories for ChromaDB (`./data/chromadb`), SQLite metadata (`./data/sqlite`), and the document repository (`./data/papers`).
    4. Service dependency order ensuring the backend is healthy before the frontend initiates API communication.
  - Containerization guarantees cross-platform executability on any evaluator machine (Windows, macOS, Linux) without requiring local installations of Python, Node.js, CUDA, or OS-level C++ compilers.

---

## 6. Academic & Course Project Compliance Specifications

In accordance with the **Course Project Submission Guidelines**:

### 6.1 Deliverable 1: Public GitHub Repository (Guidelines §3.1 — 5%)
- Repository URL MUST be public and accessible without special credentials.
- Commit history MUST show clean, phased progression across the 12-week development lifecycle.
- Secrets, large model binaries, and `.venv` environments MUST be excluded via a strict `.gitignore`.

### 6.2 Deliverable 2: Required Root README.md (Guidelines §3.2 — 5%)
The root `README.md` MUST include:
1. Problem being solved and system motivation.
2. Summary of main features and dual-engine architecture.
3. Technologies and libraries used across all 4 tiers.
4. Prerequisites, dependencies, and environment setup instructions (including both native PowerShell and `docker compose up --build` execution).
5. Step-by-step execution guide for backend and frontend.
6. Sample queries and test instructions using the bundled seed papers.
7. High-resolution screenshots of the split-screen UI and knowledge graph.

### 6.3 Deliverable 3: Executable Application & In-Class Demo (Guidelines §3.3 — 20%)
- **Demo Date:** Wednesday, December 9 in CLO 363.
- The application MUST be executable via both standard local virtual environments and Docker Compose:
  - Docker Compose enables an evaluator or instructor to launch the full stack with zero manual dependency configuration (`docker compose up --build`).
- The application MUST be demonstrated live:
  1. Ingestion of research papers.
  2. Cytoscape.js interactive graph exploration and entity filtering.
  3. Live comparative RAG query execution.
  4. Instant citation verification with PDF.js bounding-box highlight.
- The system MUST be resilient to on-the-spot instructor queries and parameter adjustments.

### 6.4 Deliverable 4: Technical Project Report (Guidelines §4 — 70% / Total Project)
The report MUST be a PDF of **not less than 20 pages** (target: 22–25 pages) structured as follows:
- **Title Page:** Project title, course name (Software Design I), student name (Chase Pluimer), instructor name, date.
- **Chapter 1: Introduction (5%):** Background, literature overload, LLM hallucination risks, motivation, and expected benefits.
- **Chapter 2: Problem Definition and Requirements Analysis (5%):** Problem formulation, target user personas (Academia, Industry, Education), functional and non-functional requirements, assumptions.
- **Chapter 3: Software Design and Architecture (15%):** Proposed solution, decoupled 4-tier architecture, component diagrams, sequence diagrams (Figure 1: 4-Tier Architecture, Figure 2: End-to-End Query Sequence, Figure 3: Knowledge Graph ER Schema).
- **Chapter 4: Implementation (25%):** Technology stack, PDF parsing with coordinate extraction, hybrid BM25 + dense retrieval, Cross-Encoder re-ranking, spaCy entity mining, Cytoscape graph rendering, split-screen UI integration.
- **Chapter 5: Testing and Results (15%):** Testing methodology (pytest unit + integration), test-results matrix table, quantitative IR benchmarks (MRR@5, latency profiling), and annotated screenshots.
- **Chapter 6: Conclusion, Limitations, and Future Work (5%):** Accomplishments, system limitations (scanned PDFs, equation rendering), future work (Graph RAG, ArXiv sync).
- **References & Appendices:** $\ge 15$ academic citations in IEEE/APA style.

### 6.5 Deliverable 5: Academic Integrity & Responsible AI Use (Guidelines §5)
- Full disclosure of AI assistant usage throughout the software development lifecycle.
- Student must fully understand and be prepared to defend all architectural choices, data structures, and code implementations.

---

## 7. Verification & Traceability Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          REQUIREMENTS TRACEABILITY MATRIX                              │
├─────────┬──────────────────────────┬────────────────────────────┬──────────────────────┤
│ Req ID  │ Source / Origin          │ Verification Method        │ Quality Gate Passed  │
├─────────┼──────────────────────────┼────────────────────────────┼──────────────────────┤
│ FR-1    │ Academic Researcher Story│ Automated pytest parser    │ Gate 1: Ingestion    │
│ FR-2    │ Industry R&D Story       │ Precision benchmark test   │ Gate 2: RAG Precision│
│ FR-3    │ Proposal S4, Constitution│ Cross-Encoder unit test    │ Gate 2: RAG Precision│
│ FR-4    │ Constitution Principle I │ Synthetic question suite   │ Gate 2 & Gate 3      │
│ FR-5    │ Undergraduate Story      │ NetworkX topology test     │ Gate 3: API Contract │
│ FR-6    │ Proposal S5, All Stories │ Playwright / UI E2E test   │ Gate 3: API Contract │
│ NFR-1   │ Proposal S7, Constitution│ `evaluate_rag.py` (MRR@5)  │ Gate 2: RAG Precision│
│ NFR-2   │ Constitution Principle I │ Automated provenance audit │ Gate 2: RAG Precision│
│ NFR-5   │ Guidelines §3, Proposal  │ Clean clone setup script   │ Gate 4: Report Align │
│ NFR-5.4 │ Guidelines §3.3, Docker  │ `docker compose up --build`│ Gate 4: Report Align │
└─────────┴──────────────────────────┴────────────────────────────┴──────────────────────┘
```

**Approval Status**: Ratified for Development  
**Next Lifecycle Step**: Proceed to Feature Specifications (`/speckit-specify`) and Implementation Planning (`/speckit-plan`).

