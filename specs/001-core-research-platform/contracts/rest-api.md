# REST API Interface Contracts: Core Grounded Literature Research Platform

> **Feature**: `001-core-research-platform`  
> **Base URL**: `http://127.0.0.1:8000/api`  
> **Interactive Swagger UI**: `http://127.0.0.1:8000/docs`  
> **Contract Protocol**: HTTP/1.1 REST, JSON payloads, Pydantic v2 validation.

---

## 1. System Health & Readiness

### `GET /api/health`
Healthcheck probe utilized by Docker Compose and container orchestrators to ensure all storage engines and models are initialized before receiving traffic.

- **Request**: No parameters.
- **Response `200 OK`**:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "sqlite_connected": true,
    "chromadb_ready": true,
    "embedding_model_loaded": true,
    "cross_encoder_loaded": true,
    "spacy_loaded": true,
    "gemini_api_configured": true
  }
  ```

---

## 2. Document Ingestion Subsystem

### `POST /api/upload`
Uploads one or more scientific PDF documents for asynchronous parsing, coordinate extraction, vectorization, and knowledge graph mining.

- **Content-Type**: `multipart/form-data`
- **Request Parameters**:
  - `files`: List of PDF binary files (`UploadFile`)
- **Response `202 Accepted`**:
  ```json
  [
    {
      "task_id": "task_9f81a7b2",
      "filename": "vaswani2017.pdf",
      "status": "parsing",
      "progress_percentage": 25,
      "error_message": null
    }
  ]
  ```

### `GET /api/documents`
Lists all indexed papers in the repository.

- **Response `200 OK`**:
  ```json
  [
    {
      "id": "paper_vaswani2017",
      "title": "Attention Is All You Need",
      "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
      "year": 2017,
      "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
      "doi": "10.48550/arXiv.1706.03762",
      "filepath": "data/papers/vaswani2017.pdf",
      "total_pages": 15,
      "created_at": "2026-10-28T12:00:00Z"
    }
  ]
  ```

### `GET /api/documents/{paper_id}/pdf`
Serves the raw binary PDF file for rendering in the PDF.js reader.

- **Path Parameter**: `paper_id` (string)
- **Response `200 OK`**: Binary stream (`application/pdf`)
- **Response `404 Not Found`**: `{"detail": "Paper with specified ID not found."}`

---

## 3. Hybrid RAG & Grounded Synthesis Subsystem

### `POST /api/query`
Executes dual BM25 + dense search, merges candidates via RRF, re-ranks using the Cross-Encoder, and generates a strictly grounded synthesis response with bounding-box citation tokens.

- **Request Body**:
  ```json
  {
    "query": "Compare the parameter efficiency and memory overhead of LoRA versus standard fine-tuning.",
    "top_k": 5,
    "paper_ids": null,
    "api_key": null
  }
  ```
- **Response `200 OK` (Grounded Synthesis)**:
  ```json
  {
    "query": "Compare the parameter efficiency and memory overhead of LoRA versus standard fine-tuning.",
    "answer": "LoRA (Low-Rank Adaptation) freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture, reducing the number of trainable parameters by up to 10,000 times and GPU memory requirements by 3-fold [paper_hu2021, Page 4]. Unlike standard full fine-tuning which requires updating all model parameters and storing optimizer states for every parameter, LoRA maintains parity in model quality while training with significantly lower VRAM overhead [paper_hu2021, Page 6].",
    "status": "success",
    "citations": [
      {
        "paper_id": "paper_hu2021",
        "paper_title": "LoRA: Low-Rank Adaptation of Large Language Models",
        "page": 4,
        "bbox": {
          "page": 4,
          "x": 0.12,
          "y": 0.35,
          "width": 0.76,
          "height": 0.14
        },
        "chunk_id": "paper_hu2021_c18",
        "relevance_score": 0.942
      },
      {
        "paper_id": "paper_hu2021",
        "paper_title": "LoRA: Low-Rank Adaptation of Large Language Models",
        "page": 6,
        "bbox": {
          "page": 6,
          "x": 0.10,
          "y": 0.58,
          "width": 0.80,
          "height": 0.16
        },
        "chunk_id": "paper_hu2021_c29",
        "relevance_score": 0.891
      }
    ],
    "model_used": "gemini-1.5-flash",
    "retrieval_latency_ms": 142.5,
    "synthesis_latency_ms": 1180.2
  }
  ```
- **Response `200 OK` (Insufficient Evidence / Zero-Hallucination Fallback)**:
  ```json
  {
    "query": "What is the quantum annealing temperature used for transformer training?",
    "answer": "The ingested literature does not contain sufficient evidence to answer this query.",
    "status": "insufficient_context",
    "citations": [],
    "model_used": "deterministic-guardrail",
    "retrieval_latency_ms": 110.2,
    "synthesis_latency_ms": 12.0
  }
  ```

---

## 4. Knowledge Graph Subsystem

### `GET /api/graph`
Returns the complete Cytoscape-compliant JSON topology of all ingested literature, entities, and relationships.

- **Query Parameters**:
  - `entity_type` (optional string): Filter by `'Paper'`, `'Author'`, `'Method'`, `'Dataset'`, or `'Metric'`.
  - `min_degree` (optional integer): Minimum connection degree threshold (default: `1`).
- **Response `200 OK`**:
  ```json
  {
    "elements": {
      "nodes": [
        {
          "data": {
            "id": "node_paper_vaswani2017",
            "label": "Attention Is All You Need",
            "type": "Paper",
            "color": "#2563EB",
            "degree": 8,
            "relevance_score": null,
            "metadata": {"year": 2017, "authors": ["Vaswani et al."]}
          }
        },
        {
          "data": {
            "id": "node_method_self_attention",
            "label": "Self-Attention",
            "type": "Method",
            "color": "#059669",
            "degree": 5,
            "relevance_score": null,
            "metadata": {}
          }
        }
      ],
      "edges": [
        {
          "data": {
            "id": "edge_1",
            "source": "node_paper_vaswani2017",
            "target": "node_method_self_attention",
            "type": "PROPOSES",
            "label": "PROPOSES",
            "weight": 1.0,
            "is_active": false
          }
        }
      ]
    },
    "total_nodes": 45,
    "total_edges": 82
  }
  ```

### `POST /api/graph/highlight`
Calculates dynamic relevance scaling and activates luminous paths for a given active query or passage list.

- **Request Body**:
  ```json
  {
    "query": "LoRA parameter efficiency",
    "active_chunk_ids": ["paper_hu2021_c18", "paper_hu2021_c29"]
  }
  ```
- **Response `200 OK`**: Returns updated `elements` with:
  - Matching nodes having `relevance_score` populated ($>0.70$) and larger rendered radii.
  - Non-matching nodes flagged with `is_dimmed: true` (opacity 20%).
  - Active traversal paths having `is_active: true` (line width 4px with bright stroke).

---

## 5. Benchmarking & Evaluation Subsystem

### `GET /api/benchmarks/run`
Executes the standardized 25-question evaluation suite against ingested seed papers, computing Mean Reciprocal Rank ($MRR@5$), Mean Average Precision ($MAP@5$), and latency breakdown.

- **Response `200 OK`**:
  ```json
  {
    "total_queries": 25,
    "mrr_at_5": 0.884,
    "map_at_5": 0.821,
    "avg_latency_ms": 164.2,
    "gate_passed": true,
    "queries": [
      {
        "query_id": "q01",
        "query": "What is the scaling factor used in scaled dot-product attention?",
        "ground_truth_chunk_ids": ["paper_vaswani2017_c12"],
        "retrieved_chunk_ids": ["paper_vaswani2017_c12", "paper_vaswani2017_c13"],
        "reciprocal_rank": 1.0,
        "precision_at_5": 1.0,
        "latency_ms": 138.4
      }
    ]
  }
  ```

