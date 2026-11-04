# Quickstart & Verification Guide: Core Grounded Literature Research Platform

> **Feature**: `001-core-research-platform`  
> **Target Audience**: Evaluators, Instructors, and Developers  
> **Verification Scenarios**: Docker Compose execution, multi-PDF ingestion, hybrid RAG comparative query, Cytoscape graph inspection, and automated benchmark verification.

---

## 1. Prerequisites

- **Container Engine**: Docker Desktop (or Docker Engine $\ge 24.0$) with Docker Compose v2.
- **Alternative Native Execution (PowerShell)**:
  - Python 3.10+
  - Node.js 18+ & npm
  - Git

---

## 2. Option A: Single-Command Docker Compose Launch (Recommended)

From the repository root (`C:\Users\Chase\Desktop\ScholarGraph\ScholarGraph`):

```bash
# 1. Clone repository (if testing clean clone)
git clone https://github.com/Chasemep/ScholarGraph.git
cd ScholarGraph

# 2. (Optional) Provide your Gemini API key in .env for generative fluency
# If omitted, the platform automatically runs in deterministic local fallback mode.
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY if desired

# 3. Launch full stack via Docker Compose
docker compose up --build
```

### Expected Startup Verification:
- **FastAPI Backend**: Online at `http://localhost:8000/docs`
- **React Frontend**: Online at `http://localhost:5173`
- **Seed Papers**: 5 seminal papers (*Attention Is All You Need, LoRA, BERT, RoFormer, FlashAttention*) are pre-warmed and ready for immediate querying.

---

## 3. Option B: Native PowerShell Development Launch

### Terminal 1: Backend API

```powershell
# Navigate to repo
cd C:\Users\Chase\Desktop\ScholarGraph\ScholarGraph

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (if fresh environment)
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Launch Uvicorn server with hot reload
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: React Frontend

```powershell
cd C:\Users\Chase\Desktop\ScholarGraph\ScholarGraph\frontend
npm install
npm run dev
```

---

## 4. End-to-End Validation Walkthrough (5-Minute Test)

### Step 1: Healthcheck Verification
Open terminal or browser:
```bash
curl http://127.0.0.1:8000/api/health
```
**Expected Outcome**: Returns HTTP `200 OK` with `"status": "healthy"`, confirm SQLite, ChromaDB, and model weights loaded.

---

### Step 2: Live Multi-Document Comparative Q&A
1. Navigate to `http://localhost:5173`.
2. In the left chat pane, submit the following query:
   ```text
   Compare the parameter efficiency and memory overhead of LoRA against standard full fine-tuning.
   ```
3. **Expected Outcome**:
   - The response renders in $< 4.0\text{ seconds}$.
   - The answer contains strict in-text citation tokens, e.g., `[LoRA Paper, Page 4]`.
   - The status is verified as `"status": "success"` with zero hallucinated assertions.

---

### Step 3: Click-to-Verify Bounding-Box Provenance
1. Click the bracketed citation badge `[LoRA Paper, Page 4]` in the synthesized answer text.
2. **Expected Outcome**:
   - The right panel immediately switches to the **PDF Reader** tab (if viewing the graph).
   - The viewer scrolls smoothly to **Page 4**.
   - A luminous, semi-transparent blue highlight overlay renders precisely over the paragraph discussing rank decomposition matrices and parameter counts.

---

### Step 4: Knowledge Graph & Prompt-Activated Highlighting
1. Switch the right panel to the **Interactive Knowledge Graph** tab.
2. Inspect the 2D Cytoscape network:
   - Blue circles represent papers.
   - Emerald diamonds represent methods (*Self-Attention*, *LoRA*).
   - Amber boxes represent datasets (*GLUE*, *SQuAD*).
3. Observe the prompt-activated relevance styling:
   - Nodes related to your previous query (*LoRA*, *GLUE*, *Edward Hu*) scale up in size.
   - The connecting path (`Paper` $\rightarrow$ `PROPOSES` $\rightarrow$ `Method` $\rightarrow$ `EVALUATES_ON` $\rightarrow$ `Dataset`) thickens with an illuminated glow.
   - Peripheral, unrelated papers (e.g., unrelated vision models) dim to 20% opacity.
4. Drag a node and observe smooth physics spring relaxation.

---

### Step 5: Run Automated IR Benchmarks (MRR@5 Gate)
Execute the benchmark harness from terminal:
```powershell
python backend/benchmarks/evaluate_rag.py
```
Or via HTTP:
```bash
curl http://127.0.0.1:8000/api/benchmarks/run
```
**Expected Outcome**:
- Executes all 25 validation queries against ground-truth passages.
- Computes Mean Reciprocal Rank ($MRR@5 \ge 0.85$).
- Outputs a formatted Markdown table matching Chapter 5 report requirements:
  ```text
  | Metric | Target | Dense-Only | BM25-Only | Hybrid RRF | Cross-Encoder Reranked |
  | MRR@5  | >=0.85 | 0.684      | 0.712     | 0.795      | 0.884 (PASS)           |
  ```

---

## 5. Automated Pytest Verification Suite

Run all unit, integration, and edge-case tests with code coverage:

```powershell
pytest tests/ -v --cov=backend --cov-report=term-missing
```

**Expected Outcome**:
- 100% of tests pass across ingestion, retrieval, neural re-ranking, graph serialization, and API endpoints.
- Coverage exceeds $\ge 80\%$.

