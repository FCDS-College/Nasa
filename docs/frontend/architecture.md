| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Belal | Approved | 0.1.0 | 2026-10-21 | M7, B1, B2, B3, B4, B5, R1-R8 | `apps/web/` |

# Frontend Architecture & Security Guide (Flame in Freefall)

This document specifies the technical architecture, security perimeter, communication flows, and environment variable configuration for the **Flame in Freefall** Next.js web application.

---

## 1. Overview & System Topology

The frontend is built using **Next.js 16 (App Router)**, **React 19**, and **Tailwind CSS**. It serves as an evidence-first scientific intelligence workspace for NASA combustion experiments in microgravity.

```
┌────────────────────────────────────────────────────────┐
│                   Browser Client                       │
│  (Next.js App Router, Tailwind, Lucide Icons, Types)   │
└───────────────────────────┬────────────────────────────┘
                            │ Same-Origin Requests (/api/...)
                            │ (No Bearer Token in Browser)
                            ▼
┌────────────────────────────────────────────────────────┐
│         Next.js Server Proxy Layer (Route Handlers)     │
│       Path: apps/web/app/api/[...path]/route.ts        │
│                                                        │
│  - Strict Allow-List: GET (health, search, etc.)       │
│  - Controlled POST: /chat (max 4 KB payload)          │
│  - Attaches: Authorization: Bearer ${FLAME_READ_TOKEN} │
│  - Error Normalization: UPSTREAM_UNAVAILABLE (502)     │
└───────────────────────────┬────────────────────────────┘
                            │ Internal Network / Upstream
                            │ FLAME_API_ORIGIN:8000
                            ▼
┌────────────────────────────────────────────────────────┐
│               Flame FastAPI Backend Service            │
│  (PostgreSQL + pgvector, MinIO S3, RQ Worker, Redis)   │
└────────────────────────────────────────────────────────┘
```

---

## 2. Server-Side Security Proxy (`app/api/[...path]/route.ts`)

To uphold NASA competition security requirements and prevent credential leaks:
1. **Token Isolation:** The browser never receives or stores the API token (`FLAME_READ_API_TOKEN`). All requests to the backend are proxied server-side where the header `Authorization: Bearer <token>` is injected.
2. **Strict Allow-List (Task B1):** The proxy enforces an explicit regular expression allowing only verified read operations:
   ```ts
   const ALLOWED = /^(health|dashboard\/counts|search|(documents|experiments|evidence|analyses)(\/[A-Za-z0-9_-]+(\/artifacts\/(original|preprocessed|mask|overlay))?)?)$/;
   ```
3. **Controlled Chat Mutation:** Only `POST /chat` is allowed for inference inquiries. Arbitrary `PUT`, `DELETE`, or unverified `POST` requests are rejected immediately with `404 Not Found`.
4. **Payload Guardrail:** The chat payload is capped at **4 KB** (`body.length <= 4096`). Oversized payloads are rejected with `400 Validation Error`.
5. **Upstream Error Normalization (Task R5):** If the backend or database is unreachable, the proxy catches the failure and returns a standardized HTTP 502 error envelope:
   ```json
   {
     "error": {
       "code": "UPSTREAM_UNAVAILABLE",
       "message": "The Flame API could not be reached.",
       "retryable": true
     }
   }
   ```

---

## 3. Data Client & Error Handling (`lib/api/client.ts`)

The frontend data client (`lib/api/client.ts`) adheres strictly to the **Evidence-First** principle:
- **Same-Origin Addressing (Task B2):** Calls use `API_BASE = ""` and target relative paths (`/api/...`). No client-side backend URLs (`NEXT_PUBLIC_API_URL` or `API_BACKEND_URL`) are used.
- **No Silent Mock Fallbacks (Task B4):** Functions never silently swap in fabricated records from `mockData.ts` when a fetch fails. If the upstream service is down, typed errors with `code: "UPSTREAM_UNAVAILABLE"` are thrown or returned.
- **Upload Validation & Integrity (Task B3):** `validateImageFile` verifies MIME types (`image/png`, `image/jpeg`), size limits (10 MB), and image pixel bounds (64x64 min, 16 MP max) before transmission. On failure, `submitFlameAnalysis` returns `UPSTREAM_UNAVAILABLE` with `retryable: true` and never fabricates a completed result.
- **No Local Persistence of Invented History (Task R4):** Historical analysis summaries are retrieved exclusively via `GET /api/analyses`. Modules `localAnalysesStore` and `localHistoryStore` are eliminated.

---

## 4. State Management

- **Research Chat (`ChatContext.tsx`):** Maintains active research threads, prompt inputs, and citation chips in React Context. Serializes conversation threads to `localStorage` under `flame_chat_sessions_v1`.
- **Client-Side vs. Server-Backed:**
  - *Client-Side State:* Active filters, modal visibility, image preview URLs, search keyword drafts, and local UI tabs.
  - *Server-Backed State:* Corpus counts, analysis results, measurement overlays, experiment conditions, and evidence provenance chains.

---

## 5. Environment Variables

The deployment environment (Railway / Docker Compose) configures the following environment variables. **No secret values are bundled into client-side JavaScript.**

| Variable | Scope | Purpose | Example / Default |
|---|---|---|---|
| `FLAME_API_ORIGIN` | Server-only | Base origin URL of the upstream FastAPI backend | `http://api:8000` (Docker) or internal Railway URL |
| `FLAME_READ_API_TOKEN` | Server-only | Secret Bearer token injected into proxied upstream requests | Pinned secret string (>= 16 chars) |
| `NODE_ENV` | Build & Runtime | Node.js execution environment | `production` / `development` |
| `PORT` | Runtime | Port on which the Next.js standalone server listens | `3000` |

---

## 6. What Is Mocked vs. Real

| Subsystem / Feature | Data Source | Notes |
|---|---|---|
| System Health (`/status`, TopBar) | **Real API** | Calls `/api/health`. Displays honest status (`OK`, `DEGRADED`, `DOWN`). |
| Dashboard Corpus Metrics (`/dashboard`) | **Real API** | Calls `/api/dashboard/counts`. Displays real document & chunk counts. |
| AI Scorecard Snapshot (`/dashboard`) | **Honest State** | Displays "Not evaluated yet" (no hardcoded passing values). |
| Scientific Search (`/search`) | **Real API** | Calls `/api/search` with hybrid lexical/semantic queries. |
| Evidence Viewer (`/evidence`) | **Real API** | Calls `/api/evidence/{id}` with SHA-256 provenance verification. |
| Document Explorer (`/documents`) | **Real API** | Calls `/api/search?type=document` and `/api/documents/{id}`. |
| Experiment Matrix (`/experiments`) | **Real API** | Calls `/api/search?type=experiment` and `/api/experiments/{id}`. |
| Flame Analysis Studio (`/analysis`) | **Real API** | Calls `POST /api/analyses` and `GET /api/analyses/{id}`. |
| Analysis History (`/history`) | **Real API** | Calls `GET /api/analyses?page_size=50`. |
| Research Chat (`/chat`) | **Real API** | Calls `POST /api/chat` through the server proxy. |
| Knowledge Base (`/knowledge`) | **Honest Empty State** | Displays "Not available yet" (endpoint deferred in v0.1 contract). |

---

## 7. Known Limitations

1. **Knowledge Extraction Graph:** The AURA knowledge entity graph endpoint is deferred in the v0.1 OpenAPI specification; the `/knowledge` page displays an informative empty state.
2. **Analysis Polling:** Live analysis creation uses 202 Accepted; the client polls `/api/analyses/{id}` until the RQ worker transitions status from `processing` to `completed`.
3. **Read-Only Dashboard:** Administrative actions (e.g., rebuilding vector index, purging quarantine) require write tokens and are reserved for Phase 2 Admin tools.
