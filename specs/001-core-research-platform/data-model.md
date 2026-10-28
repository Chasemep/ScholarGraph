# Data Models & Schemas: Core Grounded Literature Research Platform

> **Feature**: `001-core-research-platform`  
> **Date**: 2026-10-28  
> **Status**: Completed  
> **Scope**: Relational SQLite entities, vector metadata schema, Pydantic v2 domain models, and Cytoscape graph serialization formats.

---

## 1. Domain Entities & Relational Schema (SQLite)

### Table: `papers`
Stores document-level bibliographic metadata and local file references.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `TEXT` | `PRIMARY KEY` | Unique paper identifier (e.g., `paper_vaswani2017` or UUID) |
| `title` | `TEXT` | `NOT NULL` | Full title of the scientific paper |
| `authors` | `TEXT` | `NOT NULL` | JSON serialized list of author names (`["Vaswani", ...]`) |
| `year` | `INTEGER` | `NULLABLE` | Publication year |
| `abstract` | `TEXT` | `NULLABLE` | Extracted abstract text |
| `doi` | `TEXT` | `NULLABLE` | Digital Object Identifier |
| `filepath` | `TEXT` | `NOT NULL` | Relative path to stored PDF file in `./data/papers/` |
| `total_pages`| `INTEGER` | `NOT NULL` | Page count |
| `created_at` | `DATETIME`| `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Ingestion timestamp |

### Table: `paper_chunks`
Stores section-segmented text chunks with bounding-box coordinates for highlight synchronization.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `TEXT` | `PRIMARY KEY` | Unique chunk ID (e.g., `{paper_id}_c{chunk_index}`) |
| `paper_id` | `TEXT` | `NOT NULL, FOREIGN KEY (papers.id)` | Parent paper reference |
| `section` | `TEXT` | `NOT NULL` | Section heading (`Abstract`, `Methods`, `Results`, etc.) |
| `page_number`| `INTEGER` | `NOT NULL` | 1-indexed page number |
| `bbox_x` | `REAL` | `NOT NULL` | Normalized bounding box X-coordinate ($x \in [0, 1]$) |
| `bbox_y` | `REAL` | `NOT NULL` | Normalized bounding box Y-coordinate ($y \in [0, 1]$) |
| `bbox_w` | `REAL` | `NOT NULL` | Normalized bounding box width ($w \in [0, 1]$) |
| `bbox_h` | `REAL` | `NOT NULL` | Normalized bounding box height ($h \in [0, 1]$) |
| `text` | `TEXT` | `NOT NULL` | Raw chunk text content |
| `token_count`| `INTEGER` | `NOT NULL` | Approximate word/token count |

---

## 2. Vector Store Metadata Schema (ChromaDB)

Every embedding in the `scholar_chunks` collection stores 384-dimensional dense vectors (`all-MiniLM-L6-v2`) with the following metadata dictionary:

```python
{
    "paper_id": "paper_vaswani2017",
    "paper_title": "Attention Is All You Need",
    "chunk_id": "paper_vaswani2017_c14",
    "section": "Multi-Head Attention",
    "page": 4,
    "bbox_x": 0.125,
    "bbox_y": 0.342,
    "bbox_w": 0.750,
    "bbox_h": 0.115,
}
```

---

## 3. Pydantic v2 Request & Response Models

Defined in `backend/models/`:

### 3.1 Document Ingestion Models (`backend/models/paper.py`)

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class BoundingBox(BaseModel):
    page: int = Field(..., description="1-indexed page number")
    x: float = Field(..., description="Normalized horizontal coordinate [0.0 - 1.0]")
    y: float = Field(..., description="Normalized vertical coordinate [0.0 - 1.0]")
    width: float = Field(..., description="Normalized width [0.0 - 1.0]")
    height: float = Field(..., description="Normalized height [0.0 - 1.0]")

class PaperMetadata(BaseModel):
    id: str
    title: str
    authors: List[str]
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    filepath: str
    total_pages: int
    created_at: datetime

class IngestionStatus(BaseModel):
    task_id: str
    filename: str
    status: str = Field(..., description="'uploading' | 'parsing' | 'embedding' | 'ready' | 'failed'")
    progress_percentage: int
    error_message: Optional[str] = None
```

### 3.2 Hybrid RAG & Synthesis Models (`backend/models/rag.py`)

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from .paper import BoundingBox

class CitationToken(BaseModel):
    paper_id: str
    paper_title: str
    page: int
    bbox: BoundingBox
    chunk_id: str
    relevance_score: float

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, description="Natural language scientific question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top passages to inject into LLM")
    paper_ids: Optional[List[str]] = Field(default=None, description="Optional paper ID filters")
    api_key: Optional[str] = Field(default=None, description="Optional user-provided Gemini API key")

class QueryResponse(BaseModel):
    query: str
    answer: str
    status: str = Field(..., description="'success' | 'insufficient_context'")
    citations: List[CitationToken]
    model_used: str = Field(..., description="'gemini-1.5-flash' | 'extractive-fallback'")
    retrieval_latency_ms: float
    synthesis_latency_ms: float
```

### 3.3 Knowledge Graph Models (`backend/models/graph.py`)

Cytoscape.js compliant serialization:

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class CytoscapeNodeData(BaseModel):
    id: str
    label: str
    type: str = Field(..., description="'Paper' | 'Author' | 'Method' | 'Dataset' | 'Metric'")
    color: str
    degree: int = 1
    relevance_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CytoscapeNode(BaseModel):
    data: CytoscapeNodeData

class CytoscapeEdgeData(BaseModel):
    id: str
    source: str
    target: str
    type: str = Field(..., description="'AUTHORED' | 'PROPOSES' | 'EVALUATES_ON' | 'CITES' | 'ACHIEVES'")
    label: str
    weight: float = 1.0
    is_active: bool = False

class CytoscapeEdge(BaseModel):
    data: CytoscapeEdgeData

class CytoscapeElements(BaseModel):
    nodes: List[CytoscapeNode]
    edges: List[CytoscapeEdge]

class GraphResponse(BaseModel):
    elements: CytoscapeElements
    total_nodes: int
    total_edges: int
```

### 3.4 IR Evaluation Benchmark Models (`backend/models/benchmark.py`)

```python
from pydantic import BaseModel
from typing import List

class BenchmarkQueryEvaluation(BaseModel):
    query_id: str
    query: str
    ground_truth_chunk_ids: List[str]
    retrieved_chunk_ids: List[str]
    reciprocal_rank: float
    precision_at_5: float
    latency_ms: float

class BenchmarkSummary(BaseModel):
    total_queries: int
    mrr_at_5: float
    map_at_5: float
    avg_latency_ms: float
    gate_passed: bool
    queries: List[BenchmarkQueryEvaluation]
```

---

## 4. Entity State Transitions

### Document Ingestion State Machine
```
[Uploaded PDF] 
     │
     ▼
[STATUS: Parsing] ──(parse error)──> [STATUS: Failed]
     │
     ▼
[STATUS: Embedding] ──(vector store error)──> [STATUS: Failed]
     │
     ▼
[STATUS: Ready] ──> Indexed in SQLite, ChromaDB, BM25, and Knowledge Graph
```

### Query Processing Lifecycle
```
[User Query]
     │
     ▼
[Dual Retrieval: Top 20 BM25 + Top 20 ChromaDB]
     │
     ▼
[RRF Candidate Deduplication & Normalization]
     │
     ▼
[Cross-Encoder Scoring: Top 5 Filtered]
     │
     ├─(Top-5 score < 0.20 or No Evidence)──> [Output: "insufficient context"]
     │
     ▼
[Grounding Prompt Formulation with In-Text Tokens]
     │
     ▼
[LLM Synthesis / Gemini API Stream]
     │
     ▼
[QueryResponse Payload + Dynamic Graph Highlight Activation]
```

