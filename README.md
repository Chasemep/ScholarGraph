# ScholarGraph

**A Hybrid Retrieval-Augmented Generation (RAG) & Interactive Knowledge Graph Platform for Grounded Scientific Literature Synthesis**

[![CI Verification](https://img.shields.io/badge/pytest-58%20passed%20(89.46%25%20cov)-emerald)](./tests)
[![Architecture](https://img.shields.io/badge/Architecture-Decoupled%204--Tier-blue)](./Documents/ScholarGraph_Technical_Report.pdf)
[![Docker](https://img.shields.io/badge/Docker%20Compose-Ready-0db7ed)](./docker-compose.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](./backend)
[![React](https://img.shields.io/badge/React-18%20%2B%20Vite%205-61DAFB)](./frontend)

> **Course:** Software Design I  
> **Author:** Chase Pluimer  
> **Technical Report:** [`Documents/ScholarGraph_Technical_Report.pdf`](./Documents/ScholarGraph_Technical_Report.pdf)

---

## 1. Problem Being Solved

Scientific research output exceeds **5 million papers per year**, trapping researchers, R&D engineers, and students between two broken workflows:
1. **Isolated PDF Silos & Keyword Search Noise:** Traditional reference managers treat 20- to 40-page PDFs as static files. Standard `Ctrl+F` keyword search fails on conceptual synonyms, drowns users in hundreds of noisy hits across Related Work sections, and provides zero visibility into how papers, methods, datasets, and metrics connect across a field.
2. **Generative AI Hallucinations:** General-purpose AI chatbots (such as ChatGPT and Claude) frequently invent citations, fabricate page numbers, conflate experimental metrics across model sizes, and provide no direct visual proof in the source PDF.

**ScholarGraph** solves both problems through a unified **Dual-Engine Architecture**:
- **Engine 1 — Grounded Hybrid RAG with Pixel-Level PDF Provenance:** Combines sparse `BM25Okapi` lexical search with 384-dimensional `ChromaDB` dense vector embeddings (`all-MiniLM-L6-v2`), fused via **Reciprocal Rank Fusion ($k=60$)** and re-scored by a neural **Cross-Encoder (`ms-marco-MiniLM-L-6-v2`)**. Every synthesized claim includes an interactive `[paper_id, Page X]` badge that scrolls the embedded `PDF.js` reader to the exact page and paints a **luminous bounding-box highlight** over the source paragraph. Out-of-scope queries are deterministically rejected ($\tau = 0.25$) with **0% hallucinations**.
- **Engine 2 — Automated Entity Mining & Interactive Lineage Graph:** Uses `spaCy` (`en_core_web_sm`) and curated scientific pattern matchers to mine five canonical entity types (`Paper`, `Author`, `Method`, `Dataset`, `Metric`) into a directed `NetworkX` property graph rendered in a 2D `Cytoscape.js` force-directed canvas with an interactive **Node Explanation & Lineage Drawer**.

---

## 2. Main Features

- **One-Click Citation Verification (`PDF.js` Bounding-Box Overlay):** Click any inline `[paper_id, Page X]` citation badge or **Verified Source Passage** card to automatically open the target PDF, scroll to the exact page, and highlight the normalized `[page, x, y, width, height]` coordinates of the cited passage.
- **Hybrid Sparse + Dense Retrieval & Neural Cross-Encoder Re-Ranking:** Achieves **$MRR@5 = 0.912$** and **$<350\text{ ms}$ warm retrieval latency** across multi-page arXiv papers.
- **Zero-Hallucination Guardrail & Offline Fallback:** Automatically abstains (`status: "insufficient_context"`) when evidence relevance falls below $\tau = 0.25$. Supports cloud synthesis via Google's `gemini-3-flash-preview` REST API and automatically falls back to a **100% offline deterministic extractive synthesizer** if no API key is configured.
- **Interactive Knowledge Graph & Node Explanation Drawer:** Click any node (e.g., `Transformer`, `LoRA`, `WMT 2014`) to isolate its 1-hop neighborhood, read a concise definition of the concept, inspect which papers **Introduce / Propose** it versus **Build On / Evaluate** it with verbatim quotes, or click **"Synthesize Full Explanation in Chat"**.
- **Dynamic Multi-PDF Upload & Corpus Management:** Drag and drop new single-column or two-column scientific PDFs via the **Upload PDF** modal (`POST /api/upload`) with real-time progress stages (`Uploading` $\rightarrow$ `Parsing` $\rightarrow$ `Embedding` $\rightarrow$ `Ready`), or remove papers with one click.
- **Pre-Bundled Full arXiv Seed Dataset:** Ships with 5 complete foundational Transformer/LLM papers (105 total pages, 461 spatial chunks) pre-indexed for immediate evaluation.

---

## 3. Decoupled 4-Tier Architecture & Technologies Used

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         TIER 1: PRESENTATION TIER (FRONTEND)                           │
│     React 18 + Vite 5  │  Tailwind CSS  │  Cytoscape.js (Graph)  │  PDF.js (Reader)    │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ REST / JSON (OpenAPI 3.1)
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                       TIER 2: APPLICATION API TIER (BACKEND)                           │
│       FastAPI + Uvicorn  │  Pydantic v2 Schemas  │  Async Ingestion Background Tasks   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Internal Intelligence Pipeline
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                     TIER 3: AI, IR & GRAPH MODELING TIER (ENGINE)                      │
│ pdfplumber │ rank-bm25 │ all-MiniLM-L6-v2 │ Cross-Encoder │ spaCy NER │ NetworkX │ LLM │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Repository Interfaces
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                    TIER 4: DATA & PERSISTENCE TIER (STORAGE)                           │
│      ChromaDB (384-d HNSW Vectors)  │  SQLite (Relational Catalog)  │  Local PDF Store │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

| Tier | Technologies & Libraries |
| :--- | :--- |
| **Tier 1: Presentation (Frontend)** | React `18.3`, Vite `5.4`, Tailwind CSS `3.4`, `Cytoscape.js` + `cytoscape-cola`, Mozilla `pdfjs-dist`, `lucide-react`, `axios` |
| **Tier 2: Application API (Backend)** | Python `3.10+`, `FastAPI`, `Uvicorn`, `Pydantic v2` (`pydantic-settings`), `python-multipart`, `httpx` |
| **Tier 3: AI, IR & Graph Modeling** | `pdfplumber`, `pypdf`, `rank-bm25` (`BM25Okapi`), `sentence-transformers` (`all-MiniLM-L6-v2` & `cross-encoder/ms-marco-MiniLM-L-6-v2`), `spaCy` (`en_core_web_sm`), `NetworkX`, Google Gemini REST API (`gemini-3-flash-preview` + offline extractive fallback) |
| **Tier 4: Persistence & Storage** | `ChromaDB` (`PersistentClient`), `SQLite3` (`data/sqlite/scholargraph.db`), Local PDF Repository (`data/papers/`) |
| **DevOps, Containers & Testing** | `Docker` & `Docker Compose`, `Nginx` (reverse proxy), `pytest`, `pytest-cov`, GitHub Actions CI (`.github/workflows/ci.yml`) |

---

## 4. Prerequisites

You can run ScholarGraph in two ways:
- **Option A — Docker Compose (Recommended, Zero Host Dependencies):**
  - [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running (Windows, macOS, or Linux).
- **Option B — Local Native Execution (PowerShell / Terminal):**
  - **Python `3.10+`** (tested with Python 3.10, 3.11, and 3.12)
  - **Node.js `18+`** and `npm`

*(Optional)* **Gemini API Key:** All retrieval, Cross-Encoder re-ranking, entity mining, graph visualization, PDF bounding-box highlighting, and extractive synthesis work **100% offline without any API key**. To enable generative LLM prose via `gemini-3-flash-preview`, add `GEMINI_API_KEY=your_key_here` to a `.env` file in the project root (see `.env.example`).

---

## 5. Installation & Step-by-Step Execution Instructions

### Option A: Run with Docker Compose (One Command — Recommended)

1. **Clone the repository and navigate into the project directory:**
   ```powershell
   git clone https://github.com/Chasemep/ScholarGraph.git
   cd ScholarGraph
   ```
   *(If you are already inside the workspace parent directory, run `cd C:\Users\Chase\Desktop\ScholarGraph\ScholarGraph`).*

2. **(Optional) Configure `.env`:**
   ```powershell
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   # Optionally edit .env to add GEMINI_API_KEY=...
   ```

3. **Make sure Docker Desktop is running, then build and launch both containers:**
   ```powershell
   docker compose up --build
   ```
   *(To run in detached background mode, use `docker compose up --build -d`).*

4. **Access the live application:**
   - **Frontend Web Application:** [http://localhost:3000](http://localhost:3000)
   - **Backend FastAPI Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Backend Health Probe:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

5. **Stopping the containers:**
   ```powershell
   docker compose down
   ```

---

### Option B: Run Locally Without Docker (PowerShell / Virtual Environment)

1. **Create and activate the Python virtual environment & install backend dependencies:**
   ```powershell
   cd C:\Users\Chase\Desktop\ScholarGraph\ScholarGraph
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install -r backend/requirements.txt
   python -m backend.scripts.download_models
   ```

2. **Start the FastAPI backend server (Terminal 1):**
   ```powershell
   .\.venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000
   ```

3. **Install frontend dependencies and start the Vite dev server (Terminal 2):**
   ```powershell
   cd C:\Users\Chase\Desktop\ScholarGraph\ScholarGraph\frontend
   npm install
   npm run dev
   ```

4. **Access the live application:**
   - **Frontend Dev Server:** [http://localhost:5173](http://localhost:5173)
   - **Backend API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 6. Bundled Seed Corpus & Sample Walkthrough Queries

No test accounts or login credentials are required. On startup, ScholarGraph automatically indexes **5 full seminal arXiv papers** (105 pages, 461 spatial chunks):

1. **Attention Is All You Need** (*Vaswani et al., 2017* — `paper_vaswani2017`, 15 pages)
2. **BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding** (*Devlin et al., 2019* — `paper_devlin2019`, 16 pages)
3. **LoRA: Low-Rank Adaptation of Large Language Models** (*Hu et al., 2021* — `paper_hu2021`, 26 pages)
4. **RoFormer: Enhanced Transformer with Rotary Position Embedding** (*Su et al., 2021* — `paper_su2021`, 14 pages)
5. **FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness** (*Dao et al., 2022* — `paper_dao2022`, 34 pages)

### Try These Walkthrough Actions in the UI:
1. **Grounded Comparative Query & PDF Bounding-Box Verification:**
   - Paste into the left-hand chat bar:
     > `Compare the parameter efficiency and memory overhead of LoRA versus full fine-tuning.`
   - Click any inline citation badge (e.g., `hu2021 · p.8` or `hu2021 · p.4`) or **Verified Source Passage** card.
   - Watch the right pane switch to the `PDF.js` reader, scroll directly to Page 8 of *LoRA*, and highlight the exact table/paragraph bounding box in amber.
2. **Cross-Corpus Lineage Synthesis:**
   - Paste into the chat bar:
     > `Explain Transformer and compare how each paper in the corpus proposes, adapts, or evaluates it.`
3. **Interactive Knowledge Graph Exploration:**
   - Click **Graph View** or **Split View** in the top-right header.
   - Click the emerald **`Transformer`** or **`LoRA`** node on the Cytoscape canvas to isolate its 1-hop neighborhood and open the **Node Explanation & Lineage Drawer** showing which papers *Introduce / Propose* it vs. *Build On / Evaluate* it, complete with verbatim quotes and one-click page jump buttons.
4. **Custom PDF Upload:**
   - Click **Upload PDF** in the top header, drag and drop any scientific PDF (e.g., `CuckerSmale_Original.pdf`), wait for status `Ready`, and ask a question about the newly uploaded paper (e.g., `What is the Cucker-Smale model?`).

---

## 7. Automated Testing & Coverage Verification

ScholarGraph includes **58 automated unit, integration, API contract, parser, and deployment tests** achieving **89.46% backend code coverage** (enforced at $\ge 80\%$ by GitHub Actions CI in [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)):

```powershell
# Run the complete pytest suite with coverage report
.\.venv\Scripts\pytest.exe -v
```

---

## 8. User Interface Overview

The ScholarGraph workspace is organized into three synchronized views selectable from the top header:
- **Split View (Default):** Left pane houses the **Grounded Synthesis Chat** (with quick-prompt pills, inline clickable citation badges, latency/model telemetry, and Verified Source Passage cards); right pane toggles seamlessly between the **2D Cytoscape.js Knowledge Graph** and the **PDF.js Document Verifier**.
- **Graph View:** Full-width interactive `Cytoscape.js` force-directed canvas featuring color-coded entity badges (`Paper` in Blue, `Method` in Emerald, `Dataset` in Amber, `Author` in Purple, `Metric` in Rose), Core Lineage vs. All Entities toggle, search filter, and the slide-over **Node Explanation Drawer**.
- **PDF Reader View:** High-resolution `PDF.js` canvas viewer with page navigation, zoom controls ($75\%\text{--}200\%$), active section indicator, and pulsing amber bounding-box provenance overlays.
