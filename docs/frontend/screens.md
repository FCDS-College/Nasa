| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Belal | Approved | 0.1.0 | 2026-10-21 | M7, B1-B5, R1-R8 | `apps/web/app/`, `apps/web/components/` |

# Frontend Screen Inventory & API Mapping

This document provides a comprehensive inventory of all screens, views, and navigation destinations in the **Flame in Freefall** web application. It specifies routes, API endpoints, fields displayed, state behaviors (Loading, Empty, Error), test coverage, and verification data sources.

---

## 1. Master Screen Inventory Table

| Screen Name | Route | API Endpoint(s) | Role | Data Source | Primary Fields Displayed | Loading State | Empty State | Error State | Test Suite |
|---|---|---|---|---|---|---|---|---|---|
| **Scientific Dashboard** | `/dashboard`<br>`/` (redirect) | `GET /api/dashboard/counts`<br>`GET /api/health` | Viewer / Analyst | **Real API**<br>*(Snapshot: Honest)* | Document count, vector chunks, experiment runs, system status, API latency, evaluation snapshot (`Not evaluated yet`) | Skeleton metric cards with shimmer effect | Zero metrics with informative indexing hint | Error banner with retry button; health defaults to `UNKNOWN` | `tests/document-viewer.test.ts` |
| **Research Chat** | `/chat` | `POST /api/chat` | Viewer / Analyst | **Real API** | Assistant markdown response, evidence chips (ID, snippet, confidence), model name, corpus version, memory tier | Typing bubble with animated indicator | Welcome screen with scientific inquiry prompt chips | In-thread error badge with `UPSTREAM_UNAVAILABLE` retry button | `tests/chat-context.test.ts` |
| **Scientific Search** | `/search` | `GET /api/search` | Viewer / Analyst | **Real API** | Hybrid results, document/experiment titles, relevance score, snippet highlighting, domain tags | Staggered skeleton list placeholders | "No matching documents or experiments found" with refinement tips | Error card with upstream diagnostic message | `tests/search-evidence-flow.test.ts` |
| **Evidence Viewer** | `/evidence`<br>`/evidence/[id]` | `GET /api/evidence/{id}` | Viewer / Analyst | **Real API** | Evidence ID, document title, excerpt, section, page, SHA-256 hash, confidence score, claim support | Structured document skeleton placeholder | "Select an evidence item from search to view provenance" | Alert card showing upstream lookup failure | `tests/search-evidence-flow.test.ts` |
| **Document Explorer** | `/documents` | `GET /api/search?type=document`<br>`GET /api/documents/{id}` | Viewer / Analyst | **Real API** | Document title, author, year, NTRS ID, abstract, chunk count, file size, SHA-256 checksum | Table row skeleton loaders | "No documents cataloged in the active scientific corpus" | Warning banner with reconnect button | `tests/document-viewer.test.ts` |
| **Experiment Matrix** | `/experiments` | `GET /api/search?type=experiment`<br>`GET /api/experiments/{id}` | Viewer / Analyst | **Real API** | Experiment ID, rig name (BASS-II, ACME, CIR), fuel, oxidizer %, chamber pressure, flow velocity | Grid card skeletons | "No experiment records found matching filters" | Error box with retry action | `tests/document-viewer.test.ts` |
| **Flame Analysis Studio** | `/analysis` | `POST /api/analyses`<br>`GET /api/analyses/{id}`<br>`GET /api/analyses/{id}/artifacts/{type}` | Viewer / Analyst | **Real API** | Frame preview, flame area (mm²), centroid (x,y), aspect ratio, spread rate, model version, mask/overlay | Upload progress bar & processing status tracker | Interactive dropzone: "Upload flame imagery or select sample" | Honest error card (`UPSTREAM_UNAVAILABLE`) with Retry button (no fake 14082 px results) | `tests/image-upload-validation.test.ts`<br>`tests/analysis-flow.test.ts` |
| **Analysis History** | `/history` | `GET /api/analyses` | Viewer / Analyst | **Real API** | Past analyses table, thumbnail, timestamp, fuel, flame area, processing status, re-open link | Table row shimmer loaders | "No past analyses recorded. Analyze a frame in the Studio to view history." | Error panel with refresh button; zero local storage fallback | `tests/analysis-flow.test.ts` |
| **Knowledge Base** | `/knowledge` | Planned: `GET /api/knowledge` | Viewer / Analyst | **Honest Empty**<br>*(Endpoint deferred)* | Concept taxonomy, entity relationships, combustion ontology | Graph canvas skeleton | "Not available yet - Phase 2 Planned" (honest placeholder, no mock fallback) | Clear notification banner | Unit assertions verify no `mockKnowledge` leakage |
| **System Status** | `/status` | `GET /api/health` | Viewer / Admin | **Real API** | Overall status (`OK`, `DEGRADED`, `DOWN`), database connectivity, vector index latency, Redis queue, MinIO storage | Pulsing status badge & component cards | N/A (continuous telemetry) | Red degraded/unreachable banner with live reconnect trigger | `tests/analysis-flow.test.ts` |

---

## 2. Screen Details & Visual State Specifications

### 2.1 Scientific Dashboard (`/dashboard` & `/`)
- **Route:** `apps/web/app/dashboard/page.tsx`
- **Navigation:** Default entry point, linked via Sidebar icon `Home / Dashboard`.
- **Backend Calls:**
  - `GET /api/dashboard/counts`: Retrieves real total counts for documents, chunks, and experiments.
  - `GET /api/health`: Retrieves service health and latency.
- **Scorecard Integrity (Task B5):**
  - RAG Recall@5, IoU Segmentation, Factuality, and Latency cards display **"Not evaluated yet"** when not returned by an upstream evaluation endpoint.
  - Hardcoded passing numbers (`0.92`, `0.88`, `0.96`) have been permanently removed.
  - Default status is `UNKNOWN` until live response is confirmed.

### 2.2 Research Chat (`/chat`)
- **Route:** `apps/web/app/chat/page.tsx`
- **Navigation:** Sidebar icon `MessageSquare / Research Chat`.
- **Backend Calls:**
  - `POST /api/chat`: Forwarded through server proxy `apps/web/app/api/[...path]/route.ts`.
  - Enforces 4 KB request size ceiling.
- **Evidence Drill-Down:**
  - Scientific responses embed citation chips (`[E1]`, `[E2]`). Clicking an evidence chip opens provenance details or navigates directly to `/evidence/{id}`.
- **Error Handling:**
  - Displays user-friendly error banners if upstream model inference times out or fails with `UPSTREAM_UNAVAILABLE`.

### 2.3 Scientific Search (`/search`)
- **Route:** `apps/web/app/search/page.tsx`
- **Navigation:** Sidebar icon `Search / Scientific Search`.
- **Backend Calls:**
  - `GET /api/search?q={query}&mode={hybrid|vector|text}&limit={limit}`.
- **UI Modes:**
  - Hybrid search mode combining dense vector embeddings with BM25 keyword matching.
  - Filter pills for Documents, Experiments, and Evidences.

### 2.4 Evidence Viewer (`/evidence`)
- **Route:** `apps/web/app/evidence/page.tsx`
- **Navigation:** Sidebar icon `FileCheck / Evidence Viewer`.
- **Backend Calls:**
  - `GET /api/evidence/{id}`.
- **Provenance Integrity:**
  - Displays cryptographic SHA-256 hash, source document metadata, and certainty scores to satisfy NASA peer-review auditing standards.

### 2.5 Document Explorer (`/documents`)
- **Route:** `apps/web/app/documents/page.tsx`
- **Navigation:** Sidebar icon `FolderGit2 / Document Explorer`.
- **Backend Calls:**
  - `GET /api/search?type=document`.
  - `GET /api/documents/{id}`.
- **Features:**
  - Full-text search across NASA Technical Reports Server (NTRS) PDFs and Glenn Research Center papers.

### 2.6 Experiment Matrix (`/experiments`)
- **Route:** `apps/web/app/experiments/page.tsx`
- **Navigation:** Sidebar icon `FlaskConical / Experiment Matrix`.
- **Backend Calls:**
  - `GET /api/search?type=experiment`.
  - `GET /api/experiments/{id}`.
- **Features:**
  - Parametric filtering across microgravity facilities (BASS, BASS-II, ACME, CIR) with fuel compositions and atmospheric pressures.

### 2.7 Flame Analysis Studio (`/analysis`)
- **Route:** `apps/web/app/analysis/page.tsx`
- **Navigation:** Sidebar icon `Flame / Analysis Studio`.
- **Backend Calls:**
  - `POST /api/analyses`: Initiates image segmentation job.
  - `GET /api/analyses/{id}`: Polls for completion.
  - `GET /api/analyses/{id}/artifacts/{original|preprocessed|mask|overlay}`: Loads binary images.
- **Anti-Mock Remediation (Task B3):**
  - If the backend is unavailable or fails, the interface renders an error card with code `UPSTREAM_UNAVAILABLE` and an interactive **Retry** button.
  - Simulated fallback with fake YOLOv8 (14,082 px flame area) is strictly abolished.

### 2.8 Analysis History (`/history`)
- **Route:** `apps/web/app/history/page.tsx`
- **Navigation:** Sidebar icon `History / History`.
- **Backend Calls:**
  - `GET /api/analyses?page_size=50`.
- **Anti-Mock Remediation (Task R4):**
  - Historical records are loaded from the backend API.
  - In-memory fake stores (`localAnalysesStore`, `localHistoryStore`) are removed.

### 2.9 Knowledge Base (`/knowledge`)
- **Route:** `apps/web/app/knowledge/page.tsx`
- **Navigation:** Sidebar icon `Network / Knowledge Base`.
- **Data Source (Task R3):**
  - Displays **"Not available yet - Phase 2 Planned"** empty state.
  - No fake graph entities (`mockKnowledge`) are displayed.

### 2.10 System Health (`/status`)
- **Route:** `apps/web/app/status/page.tsx`
- **Navigation:** Sidebar icon `Activity / System Status` and TopBar health indicator.
- **Backend Calls:**
  - `GET /api/health`.
- **Telemetry Indicators:**
  - Real-time latency, component uptime, database connectivity, and vector index health.

---

## 3. Sidebar Navigation Verification (Task R8)

All 10 navigation links are present in `apps/web/components/layout/Sidebar.tsx` and have been verified to resolve without 404 errors:

1. `/dashboard` - Scientific Dashboard
2. `/chat` - Research Chat
3. `/search` - Scientific Search
4. `/evidence` - Evidence Viewer
5. `/documents` - Document Explorer
6. `/experiments` - Experiment Matrix
7. `/analysis` - Flame Analysis Studio
8. `/history` - Analysis History
9. `/knowledge` - Knowledge Base
10. `/status` - System Status

---

## 4. Known Limitations

1. **Deferred Knowledge Endpoint:** Phase 1 backend OpenAPI schema does not yet include `/knowledge` graph endpoints; the UI renders an honest "Not available yet" message.
2. **Analysis Async Processing:** Processing large high-resolution flame video frames requires asynchronous RQ worker execution; client uses polling with a 15-second timeout.
