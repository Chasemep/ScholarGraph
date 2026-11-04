# Feature Specification: Core Grounded Literature Research Platform

**Feature Branch**: `001-core-research-platform`  
**Created**: 2026-10-28  
**Status**: Draft  
**Input**: User description: "(Recommended) Full Core Platform: End-to-end literature research system (PDF Ingestion, Hybrid RAG with Cross-Encoder, Knowledge Graph, and Split-Screen Reader)"

---

## Clarifications

### Session 2026-10-28

- Q: How should the platform execute the final natural language generation for grounded synthesis answers? → A: Multi-Provider LLM Engine defaulting to Google Gemini API (configured via `.env` or UI settings) for high-speed synthesis, with automatic local fallback when no API key is provided.
- Q: How should the interactive Knowledge Graph canvas be integrated into the split-screen user workspace? → A: Tabbed right panel layout where the left pane remains fixed for comparative Q&A chat, while the right pane toggles seamlessly between the interactive Cytoscape graph canvas and the synchronized PDF.js reader.
- Q: How should the platform manage scientific entity extraction and knowledge graph curation? → A: Automated extraction with interactive exploration: entities and relations are mined automatically on upload; graph canvas supports rich filtering, inspection, and neighborhood expansion without manual editing overhead.
- Q: How should the retrieval precision benchmark suite (MRR@5 evaluation) be packaged and executed? → A: Bundled 25-question standardized benchmark suite across seed papers, executable via a dedicated evaluation harness script and API endpoint, generating formatted performance tables directly usable in the technical report.
- Q: How should the platform handle document ingestion processing and status reporting when users upload papers? → A: Asynchronous background processing with staged progress tracking: background ingestion pipeline reports granular statuses (Uploading → Parsing Sections → Generating Vectors → Ready) without freezing user workspace interactions on already-indexed papers.
- Q: How are graph node sizes, edge weights, and prompt-based interactions determined? → A: Dual-mode interactive visualization: in idle state, node sizes scale with connectivity degree; upon active search prompts, relevant nodes dynamically scale up with neural relevance scores, connecting relational edges thicken and illuminate, and non-relevant nodes dim to 20% opacity.
- Q: How should automated testing and continuous integration be enforced across the project lifecycle? → A: Test-driven verification across all phases: each major implementation is accompanied by persistent pytest unit and edge-case test suites, executed automatically on every push via a GitHub Actions CI workflow.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Document Comparative Q&A with Click-to-Verify Provenance (Priority: P1)

A researcher or engineer needs to pose nuanced, comparative questions across multiple scientific papers (e.g., comparing benchmark accuracy, computational complexity, or architectural differences) and receive a synthesized, strictly factual response. Every factual assertion must be accompanied by a clickable citation token that immediately opens the source document to the exact page and visually highlights the supporting paragraph or table.

**Why this priority**: This constitutes the core intellectual value of the platform. Eliminating generative hallucinations and providing deterministic verification directly solves the primary crisis of trust in AI-assisted literature review.

**Independent Test**: Can be independently tested by querying a pre-ingested collection of two related papers on a specific comparative metric (e.g., parameter count or accuracy score), verifying that the generated answer cites both papers accurately, clicking each citation token, and confirming that the reader navigates to the exact page with the relevant text highlighted.

**Acceptance Scenarios**:

1. **Given** a collection of ingested papers containing empirical evaluation results,  
   **When** a user submits a comparative question such as "Compare the parameter efficiency and memory overhead between Method A and Method B",  
   **Then** the system produces a synthesized comparison where every claim links directly to a verifiable citation token containing paper ID, page number, and paragraph location.

2. **Given** a generated answer with citation tokens,  
   **When** the user clicks any citation badge,  
   **Then** the document viewer immediately jumps to the designated page and paints a visible highlight over the exact source bounding box.

3. **Given** an ingested collection that does NOT contain information relevant to the user's query,  
   **When** the user asks a question not addressed in the literature,  
   **Then** the system deterministically outputs an explicit notification that the corpus contains insufficient evidence, refusing to fabricate an answer.

---

### User Story 2 - Visual Knowledge Graph & Concept Lineage Exploration (Priority: P2)

A student or researcher entering an unfamiliar subfield needs a visual, relational map showing how papers, authors, methodologies, datasets, and performance metrics interconnect. They need to navigate beyond flat lists of search results to explore conceptual lineage, identify seminal baseline architectures, and inspect which methods have been evaluated on specific benchmark datasets.

**Why this priority**: Bridges the cognitive gap for students and literature reviewers by visually mapping complex citation hierarchies and methodological evolution across competing research efforts.

**Independent Test**: Can be tested independently by opening the knowledge graph view for an ingested paper corpus, expanding an entity node (such as a named methodology), filtering connected papers by topic, and selecting a node to inspect its associated metadata and source documents.

**Acceptance Scenarios**:

1. **Given** an ingested corpus of related scientific documents,  
   **When** the user navigates to the knowledge graph canvas,  
   **Then** the system renders an interactive 2D network displaying entity nodes (Papers, Authors, Methods, Datasets, Metrics) connected by typed relational links (Authored, Proposes, Evaluates On, Cites).

2. **Given** the rendered knowledge graph,  
   **When** the user clicks an entity node (e.g., a specific Dataset or Author),  
   **Then** the canvas filters the display to highlight connected nodes and reveals a contextual inspection panel detailing all associated literature.

3. **Given** the interactive graph view,  
   **When** the user searches for a specific concept or applies category filters,  
   **Then** non-matching nodes are dimmed or hidden, allowing focused exploration of targeted research sub-domains.

4. **Given** an active Q&A query submitted in the chat pane,  
   **When** synthesis results are generated,  
   **Then** the knowledge graph dynamically reflects prompt relevance: matching entity nodes scale up in size proportionally to their neural relevance scores, connecting relational edges thicken with luminous highlighting, and non-relevant nodes fade to a 20% translucent background.

---

### User Story 3 - Section-Aware Document Ingestion & Spatial Coordinate Tracking (Priority: P3)

A user uploads a batch of scientific research papers in PDF format. The system automatically extracts structured document components—including titles, author rosters, abstracts, section headings, body paragraphs, and tabular results—while capturing the exact spatial bounding coordinates for every text segment on each page to enable downstream visual verification.

**Why this priority**: Serves as the foundational data pipeline that feeds both the hybrid retrieval index and the knowledge graph builder. Without spatial coordinate tracking, pixel-level provenance is impossible.

**Independent Test**: Can be independently tested by uploading a complex 15-page academic paper, verifying that the document is parsed into distinct sections without character corruption, and confirming that every extracted chunk records its page number and bounding-box coordinates.

**Acceptance Scenarios**:

1. **Given** a collection of up to 20 academic PDF files,  
   **When** the user uploads the documents via the interface,  
   **Then** the system processes each file, categorizes text blocks into logical sections (Abstract, Methods, Results, References), and stores extracted metadata in the document catalog.

2. **Given** scientific text containing mathematical expressions and Greek symbols,  
   **When** text is parsed and indexed,  
   **Then** special characters and formulas are preserved intact without encoding corruption.

3. **Given** a newly ingested paper,  
   **When** ingestion completes,  
   **Then** the paper's contents are immediately queryable via search and reflected in the relational knowledge graph.

---

### User Story 4 - One-Command Containerized Execution (Priority: P4)

A course evaluator, developer, or researcher needs to clone the project repository and launch the complete multi-tier application (frontend interface, backend services, AI models, and document storage) using a single standard command, without experiencing dependency conflicts or needing to manually configure Python runtimes, Node.js environments, or machine-specific C++ build tools.

**Why this priority**: Critical for academic reproducibility and frictionless evaluation. Directly fulfills course project grading mandates requiring the application to be executable out of the box in under 5 minutes.

**Independent Test**: Can be independently tested on a clean machine by cloning the repository, running the container orchestration startup command, and verifying that both the web user interface and the backend services become fully accessible and healthy within the specified time threshold.

**Acceptance Scenarios**:

1. **Given** a system with standard container runtime software installed,  
   **When** the user issues the single container launch command,  
   **Then** all application tiers build and start up automatically, exposing the web interface and API endpoints.

2. **Given** a cold launch with pre-bundled seed papers,  
   **When** the application reaches the ready state,  
   **Then** the seed documents are pre-loaded and ready for immediate interactive Q&A and graph exploration without manual data entry.

---

### User Story 5 - Continuous Automated Testing & GitHub Actions CI Gate (Priority: P2)

Developers, evaluators, and contributors pushing changes to the repository require immediate, automated verification that new features adhere to specifications and do not introduce regressions into existing components. Every major implementation module across all development phases (PDF parsing, vector and lexical retrieval, neural re-ranking, knowledge graph modeling, and API endpoints) must be covered by automated test suites testing general scenarios and edge cases. These tests must persist permanently in the repository and execute automatically via a GitHub Actions continuous integration (CI) pipeline on every code push and pull request.

**Why this priority**: Guarantees code stability and regression-free development across the 12-week course timeline. Directly generates the automated test-results matrix and defect logs mandated by Course Guidelines Chapter 5 (15% of total grade).

**Independent Test**: Can be tested independently by pushing a code change or creating a pull request on GitHub, verifying that the GitHub Actions CI workflow triggers automatically, executes all test suites, and blocks merges if any unit, integration, or edge-case test fails.

**Acceptance Scenarios**:

1. **Given** a code commit pushed to any branch or pull request targeting the repository,  
   **When** the GitHub Actions workflow executes,  
   **Then** the entire automated test suite runs in a clean virtualized environment, validating both general use cases and edge cases across all implemented subsystems.

2. **Given** an accidental regression or breaking change introduced into a previously completed phase (e.g., coordinate extraction or hybrid RAG retrieval precision),  
   **When** the automated tests execute,  
   **Then** the CI workflow fails deterministically, marking the commit with a red failure badge and outputting detailed diagnostic traces.

3. **Given** a successful test run on GitHub,  
   **When** all tests pass,  
   **Then** an automated code coverage report is generated, confirming that test coverage meets or exceeds the required threshold.

---

### Edge Cases

- **Insufficient Corpus Evidence**: What happens when a user submits a query that cannot be answered using the ingested documents? The system MUST output an explicit "insufficient context" message rather than guessing or generating unsubstantiated assertions.
- **Corrupted or Password-Protected PDFs**: How does the system handle an unreadable or malformed PDF upload? The background ingestion pipeline MUST flag the specific document status as "Failed" with an explanatory error badge, isolating the failure so it does not interrupt other running ingestion jobs or crash the service.
- **Complex Mathematical Notation & Acronyms**: How does the system ensure queries for exact formulas or obscure acronyms return accurate passages? Dual lexical and semantic retrieval MUST combine exact term matching with concept similarity to prevent semantic search from masking exact symbol matches.
- **High Node Density in Knowledge Graph**: What happens when a large document collection produces hundreds of interconnected nodes? The graph canvas MUST provide responsive zoom, pan, and clustering controls so that visualization performance remains fluid without browser lag.
- **Multi-Page Figure or Table References**: How does the system handle citations referencing tables spanning page boundaries? The citation token MUST link to the primary initiating page and bounding box where the relevant finding is stated.
- **External API Dependency in CI**: How do automated tests verify generative synthesis in GitHub Actions without relying on external network calls or leaking secrets? Tests MUST employ fixture mocks for external synthesis APIs while exercising the full prompt construction and fallback logic deterministically.
- **Continuous Integration Test Runtime**: How does the CI pipeline avoid slow builds when downloading transformer models? The GitHub Actions workflow MUST implement dependency and model cache layers so that full test execution completes in under 3 minutes.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an asynchronous document ingestion pipeline accepting multi-PDF uploads, generating immediate task tracking identifiers and reporting staged progress status (Uploading → Parsing Sections → Generating Vectors → Ready) without blocking user interaction with already-indexed literature.
- **FR-002**: System MUST parse uploaded documents into structured sections (Title, Abstract, Section Headings, Body Paragraphs, Tables, References) while preserving text formatting and character encoding.
- **FR-003**: System MUST record spatial page coordinates (page number and bounding box geometry) for each parsed paragraph and table cell.
- **FR-004**: System MUST maintain a dual-search retrieval index combining exact keyword matching with semantic vector similarity.
- **FR-005**: System MUST merge and re-rank candidate search passages using neural cross-attention scoring to identify the most relevant context passages.
- **FR-006**: System MUST generate synthesized answers strictly constrained to the retrieved context passages, prohibiting generative speculation outside the provided text. Synthesis MUST support a primary Google Gemini API generative pathway (configured via environment variable or UI input) with an automatic local fallback pathway when no external API key is present.
- **FR-007**: System MUST embed deterministic citation tokens within every synthesized claim, linking the claim to its source document ID, page number, and bounding box coordinates.
- **FR-008**: System MUST deterministically decline to answer and output an explicit status message whenever the retrieved passages do not contain sufficient evidence to answer the user query.
- **FR-009**: System MUST automatically extract scientific entities (including Papers, Authors, Methodologies, Datasets, and Metrics) from the ingested literature during document parsing, without requiring manual entity tagging.
- **FR-010**: System MUST model and visualize a deterministic directed relationship network of extracted entities and typed links (Authored, Proposes, Evaluates On, Cites) in an interactive 2D graph canvas with category filtering and neighborhood inspection.
- **FR-011**: System MUST support dual-state graph visualization: in idle state, node sizes MUST reflect overall topological connectivity degree; upon active search queries, nodes directly relevant to the retrieved answer passages MUST dynamically scale in size proportional to their neural relevance score, connecting relational edges MUST thicken with luminous highlighting, and non-relevant nodes MUST dim to a 20% translucent background state. Users MUST also be able to manually zoom, pan, and inspect entity nodes and their connected literature within the canvas.
- **FR-012**: System MUST provide a split-screen workspace featuring a persistent left pane for comparative Q&A chat and a tabbed right pane that toggles seamlessly between the interactive 2D knowledge graph canvas and the integrated document reader.
- **FR-013**: System MUST automatically switch the right pane to the document reader tab (if currently on the graph tab), scroll to the target page, and apply a visible highlight over the cited bounding box whenever a user clicks a citation badge.
- **FR-014**: System MUST bundle a representative seed dataset of seminal open-access scientific papers pre-configured for immediate demonstration.
- **FR-015**: System MUST provide single-command containerized execution orchestrating all application components and persistent data volumes.
- **FR-016**: System MUST provide an automated retrieval evaluation harness containing a standardized suite of 25 domain questions with ground-truth passage bindings, executable via CLI script and API endpoint to output formatted precision (MRR@5, MAP@5) and latency tables.
- **FR-017**: System MUST provide automated test suites accompanying each major implementation module across all development phases (document parsing, coordinate tracking, hybrid search, neural re-ranking, knowledge graph mining, and API endpoints) testing both nominal execution scenarios and edge cases.
- **FR-018**: System MUST integrate an automated continuous integration (CI) workflow using GitHub Actions that executes the complete automated test suite upon every push and pull request to the repository.
- **FR-019**: All automated test suites MUST persist permanently in the repository and maintain regression-free pass status throughout all subsequent project phases.

---

### Key Entities *(include if feature involves data)*

- **Paper**: Represents an ingested academic document with associated metadata (title, author list, publication year, abstract, digital object identifier, and local file storage location).
- **Author**: Represents an academic researcher or creator associated with one or more authored papers.
- **Methodology**: Represents a computational model, algorithm, architectural technique, or experimental procedure proposed or evaluated within the literature.
- **Dataset**: Represents an empirical benchmark, corpus, or data collection used to train or evaluate methodologies.
- **Metric**: Represents a quantitative evaluation measure, benchmark score, throughput figure, or performance comparison reported in the literature.
- **Text Passage Chunk**: Represents a discrete segment of document text associated with a specific section header, page number, and spatial bounding box coordinates.
- **Citation Provenance**: Represents the deterministic binding between an assertion in a synthesized answer and the specific source passage chunk coordinates.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (Retrieval Precision)**: The retrieval engine achieves a Mean Reciprocal Rank at top 5 (MRR@5) of at least 0.85 across the standardized 25-question validation suite evaluated via the automated benchmarking harness.
- **SC-002 (Zero-Hallucination Rate)**: 100% of synthesized claims produced by the system are traceable to verified source passage citations; 0.0% ungrounded assertions are generated.
- **SC-003 (Retrieval Latency)**: Retrieval of relevant candidate passages across an ingested corpus of up to 20 papers completes in under 2.0 seconds.
- **SC-004 (End-to-End Synthesis Response Time)**: Full query synthesis including retrieval, passage re-ranking, and grounded generation completes in under 4.0 seconds on standard consumer hardware.
- **SC-005 (Verification Efficiency)**: Users can visually verify any synthesized claim in fewer than 2 clicks (one click on the citation token immediately reveals the highlighted source text in the reader).
- **SC-006 (Knowledge Graph Fluidity)**: The interactive graph canvas renders and completes automatic layout positioning in under 1.0 second for networks containing up to 100 nodes.
- **SC-007 (Frictionless Deployment)**: An evaluator can launch the entire operational platform from a clean clone using a single container command, achieving full system availability in under 5 minutes.
- **SC-008 (Continuous Integration Reliability)**: 100% of code commits and pull requests trigger and pass the automated GitHub Actions CI workflow, with automated test suite execution completing in under 3 minutes.
- **SC-009 (Test Persistence & Regression Prevention)**: Automated test suites achieve at least 80% code coverage across backend application logic, with zero lingering regression failures throughout all project development phases.

---

## Assumptions

- **Document Format**: Input research papers are accessible as standard digital PDF documents containing embedded text layers. Scanned bitmap PDFs requiring optical character recognition (OCR) are considered out of scope for the baseline release.
- **Computational Hardware**: The platform is engineered to execute efficiently on standard multi-core consumer CPUs without requiring dedicated enterprise GPU hardware, though GPU acceleration may be utilized when available.
- **Evaluation Dataset**: A curated seed collection of 5–8 high-impact open-access computer science papers (e.g., Attention Is All You Need, LoRA, BERT) is packaged with the application to provide immediate evaluation capabilities upon first startup.
- **Local Autonomy**: Core literature search, neural re-ranking, entity extraction, and graph rendering execute locally without mandatory reliance on paid, proprietary cloud API services.

