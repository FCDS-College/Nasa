# FastAPI ↔ Next.js integration audit

| Owner | Status | Date | Scope |
|---|---|---|---|
| Lead (Anas) | Read-only audit, no fixes applied | 2026-11-13 | `apps/api/flame_api/` ↔ `apps/web/` at `36fb667` plus the uncommitted working tree |

This is the `.NET ↔ Flutter` integration-audit method applied to this stack: FastAPI in place of .NET, and the Next.js dashboard in place of Flutter. The audit itself changed no source files.

**Remediation status (2026-11-13):** the P0 items **INT-001, INT-002, INT-003 and INT-004 are fixed** in `apps/web` (frontend only; no API or contract change):
- `types.ts` has the contract's `ReviewStatus` and `AnalysisStatus` enums.
- `client.ts` maps values through `toReviewStatus` and `toAnalysisStatus`, and `submitChat` throws a `ChatError` carrying the code, message, HTTP status and `Retry-After`.
- The evidence, history and analysis pages render every contract state.
- The chat page shows the API's error as an error turn and caps input at 500 characters.

Verified with `tsc --noEmit` and ESLint (both clean), plus a mocked-`fetch` script covering every enum value and the 429, 400, 503 and network-failure chat paths. Not yet checked in a browser. The other findings are still open.

---

## 1. Executive summary

**Integration health: good at the transport and auth layer. Several contract mismatches at the semantic layer, all in the frontend's mapping code.**

The dashboard never talks to FastAPI directly. Every browser call goes to the same-origin Next.js route handler `apps/web/app/api/[...path]/route.ts`. That handler allowlists read paths and `POST /api/chat`, and attaches a read-scoped bearer token on the server. Both sides agree on URLs, verbs, auth scope, query parameters and the error envelope. The TypeScript build and lint are clean.

The defects sit where the frontend turns backend JSON into its own types, through loosely typed `Record<string, any>` mapping:

- **Evidence review status never matches** (INT-001). The backend sends `machine_extracted` / `human_verified` / `rejected`, but the UI tests for `"verified"`. Human-verified evidence is therefore labelled "Unreviewed Record". The contract explicitly says the UI must distinguish it.
- **Cancelled analyses show as permanently in progress** (INT-002).
- **Errors are swallowed.** On the chat page, a 429 rate limit, a 400 validation error and an outage all render as the same "connection failed" answer (INT-003). On read pages, 401, 429 and 503 render as "not found" or as an empty list (INT-005).
- **All dashboard users share one rate-limit bucket**, because the proxy uses a single API key (INT-014). Chat defaults to 30 requests a minute for the whole site.

**Counts**

| Severity | Confirmed | Likely | Needs runtime verification | Total |
|---|---|---|---|---|
| Critical | 0 | 0 | 0 | 0 |
| High | 0 | 0 | 0 | 0 |
| Medium | 5 | 0 | 0 | 5 |
| Low | 5 | 1 | 0 | 6 |
| Informational | 3 | 0 | 0 | 3 |
| **Total** | **13** | **1** | **0** | **14** |

**Limitations:** this was a static trace, plus the existing backend tests, `tsc` and ESLint. The stack was not run end to end, and no HTTP calls were made against a live API. Admin routes were checked only to confirm the proxy cannot reach them, because the dashboard does not use them.

---

## 2. System map

```
Browser (client components, all "use client")
  ├─ lib/api/client.ts        getJson / submitChat / fetch* mappers  ──┐
  ├─ lib/api/fireSafety.ts    typed get<T>() + ApiError               ──┤  fetch(`${NEXT_PUBLIC_API_URL ?? ""}/api/...`)
  ├─ components/fire/VideoAnalysisPanel.tsx  own getJson             ──┤
  └─ lib/context/ChatContext.tsx  chat state, localStorage persistence ┘
                     │ same origin
                     ▼
Next.js route handler  app/api/[...path]/route.ts
  GET : regex allowlist → `${FLAME_API_ORIGIN}/api/<path>?<query>`, 20 s timeout
  POST: only "chat", body ≤ 4096 chars, 130 s timeout
  attaches  Authorization: Bearer $FLAME_READ_API_TOKEN  (server-side only)
  forwards  status + body stream + content-type / cache-control / retry-after
                     │
                     ▼
FastAPI  flame_api/main.py
  middleware request_context → _authorized: scope = admin | read (GET/HEAD + POST /api/chat) | write
           → _identify (legacy token or flk_ client key) → 401 / 403 / 503
           → _rate_limited (per identity, Redis) → 429 + Retry-After
  exception handlers: RequestValidationError→400 VALIDATION_ERROR, SQLAlchemyError→503,
                      HTTPException 404/405, Exception→500     (envelope: contracts.error_body)
  routers: main.py (health, dashboard, search, chat, documents, experiments, evidence)
           analysis.py, investigations.py, graph.py, admin.py
  served OpenAPI = hand-written docs/api/openapi.json (app.openapi = _contract_openapi), v0.7.0
```

The error envelope is the same on every backend path: `{"error": {code, message, request_id, retryable, field_errors[], details{}}}` (`apps/api/flame_api/contracts.py:18-36`). The proxy's own errors follow the same `error.code` shape.

---

## 3. Endpoint contract matrix

| # | Frontend caller | Method + path (via proxy) | Proxy allows | Backend handler | Request | Response mapping | Status |
|---|---|---|---|---|---|---|---|
| 1 | `client.ts:30 fetchHealth` | GET `/api/health` | yes | `main.py:295` | – | `healthy/degraded/unhealthy` → `ok/degraded/down`; reads the body on 503 as intended | Compatible |
| 2 | `client.ts:56 fetchDashboardData`, `fireSafety.ts:205 fetchCounts` | GET `/api/dashboard/counts` | yes | `main.py:428` | – | `documents, chunks, indexed_chunks, knowledge_version` | Compatible |
| 3 | `client.ts:74 submitChat` / `ChatContext.tsx:173` | POST `/api/chat` | yes (only POST) | `main.py:772` | `{query, conversation_id}`; backend `query` 1–500 chars | shape matches `ChatResponse`; errors are lost (INT-003); `conversation_id` is ignored (INT-007); no 500-char limit on the client (INT-004) | Mismatch |
| 4 | `client.ts:90 searchResearch` | GET `/api/search?q&domain` | yes | `main.py:518` | `domain ∈ {combustion, all}` ✓ | `locator.page` is typed string but is an int (INT-009) | Compatible (type drift) |
| 5 | `client.ts:115 fetchEvidence` | GET `/api/evidence/{id}` | yes | `main.py:1049` (ULID) | client regex is looser than ULID → 400 → null | `review_status` and `kind` enums are wrong (INT-001, INT-009); errors read as "not found" (INT-005) | Mismatch |
| 6 | `client.ts:156 fetchAnalysis` | GET `/api/analyses?status=completed&page_size=20`, `/api/analyses/{id}` | yes | `analysis.py:338, 393` | `status` list ✓, `page_size ≤ 100` ✓ | `cancelled` → `"pending"` (INT-002); picks images from only the 20 newest (INT-010) | Mismatch |
| 7 | `client.ts:26 artifactUrl` | GET `/api/analyses/{id}/artifacts/{kind}` | yes, `original/preprocessed/mask/overlay` | `analysis.py:437`, same kinds | – | binary + immutable cache header forwarded | Compatible |
| 8 | `client.ts:190 fetchAnalysesHistory` | GET `/api/analyses?page_size=50` | yes | `analysis.py:338` | ✓ | `queued`/`cancelled` → `"processing"` (INT-002); errors → `[]` (INT-005) | Mismatch |
| 9 | `client.ts:207 fetchExperiments` | GET `/api/search?q=flame&type=experiment&domain=all&page_size=20` + N× `/api/experiments/{id}` | yes | `main.py:518, 1024` | ✓ | lists experiments through a keyword search; 21 calls (INT-008) | Compatible (fragile) |
| 10 | `client.ts:186 fetchKnowledge` | none (returns `[]`) | `graph/*` is not allowlisted | `graph.py:62, 96` exist and are in the contract | – | the page is always empty (INT-006) | Mismatch (not wired) |
| 11 | `fireSafety.ts:186 fetchInvestigations` | GET `/api/investigations?scenario \| o2_fraction&pressure_kpa` | yes | `investigations.py:155` | sends both custom values or neither ✓ | typed `InvestigationList` matches the payload | Compatible |
| 12 | `fireSafety.ts:188 fetchInvestigation` | GET `/api/investigations/{FF-…}` | regex `FF-[A-Z0-9-]{2,41}` | pattern `^FF-[A-Z0-9][A-Z0-9-]{1,40}$` | equivalent except a leading dash (backend 400, fine) | ✓ | Compatible |
| 13 | `fireSafety.ts:191 fetchInsights` | GET `/api/insights` | yes | `investigations.py:223` | ✓ | ✓ | Compatible |
| 14 | `fireSafety.ts:202 fetchFlexOutcome` | GET `/api/insights/flex-outcome` | yes | `investigations.py:320` | `fuel` literal, ranges and sum check ✓; `field_errors` shown ✓ | ✓ | Compatible |
| 15 | `VideoAnalysisPanel.tsx:66` | GET `/api/analyses?status=completed&page_size=50`, `/api/analyses/{id}` | yes | `analysis.py` | ✓ | contract 0.7.0 `result.audio` is not rendered (INT-012) | Compatible |
| – | (none) | GET `/api/documents`, `/api/documents/{id}`, `/api/experiments` | yes | `main.py:916, 996, 952` | – | unused by the UI | Not inspected (no caller) |
| – | (none) | POST `/api/analyses`, `/cancel`, `/api/admin/*`, `/api/ai/providers` | **no** (404 at the proxy) | write/admin scope | – | correctly unreachable from the browser | Compatible (by design) |

---

## 4. Findings

### [INT-001] Evidence `review_status` enum mismatch hides human verification
- **Severity:** Medium
- **Confidence:** Confirmed
- **Integration area:** Response DTO
- **Evidence:** frontend `apps/web/lib/api/types.ts:76` (`"verified" | "pending" | "rejected"`), `apps/web/lib/api/client.ts:125` (passes the raw value, defaults to `"pending"`), `apps/web/app/evidence/page.tsx:49-50` (`=== "verified"`), `:116`. Backend `apps/api/flame_api/ingest.py:213`, `:699`, `worker.py:512` (`machine_extracted`), `admin.py:209` (`machine_extracted | human_verified | rejected`). Contract: `docs/api/openapi.json` `ReviewStatus` = `raw, machine_extracted, human_verified, rejected`, with the note *"The UI must visibly distinguish human_verified"*.
- **Mismatch:** the frontend expects `verified`, which the backend never sends.
- **Trigger:** an admin calls `PUT /api/admin/evidence/{id}/review` with `human_verified`, then the evidence page is opened.
- **Impact:** human-verified evidence carries the "Unreviewed Record" badge. Rejected evidence gets the same neutral badge (only the small detail text says `REJECTED`). The provenance signal the contract requires is lost. Chat and search already exclude rejected evidence, so this only affects deep links to the evidence page.
- **Safeguards:** none. The value goes through an untyped `Json` map, so `tsc` cannot catch it.
- **Fix direction:** change `EvidenceRecord.review_status` to the contract enum, badge on `human_verified`, and give `rejected` a danger variant.
- **Regression test:** a component or unit test that maps an evidence fixture with each contract value and asserts the badge text and variant.
- **Validation:** static trace.

### [INT-002] Cancelled (and queued) analyses render as "pending" or "processing" forever
- **Severity:** Medium
- **Confidence:** Confirmed
- **Integration area:** Response DTO / State
- **Evidence:** `apps/web/lib/api/client.ts:168` (any status other than completed or failed → `"pending"`), `:197` (→ `"processing"`), `apps/web/app/history/page.tsx:81` (spinning clock). Backend: `analysis.py:422`, `worker.py:53`, `:950` set `cancelled`; the contract `AnalysisStatus` lists `cancelled` as terminal.
- **Mismatch:** the frontend has three states; the backend has five, `cancelled` among them as a terminal state.
- **Trigger:** cancel a queued analysis (`POST /api/analyses/{id}/cancel`), or let job recovery cancel a stuck one, then open History or `/analysis?id=…`.
- **Impact:** the user sees a job "in progress" that will never finish. `failure.message` is not shown either.
- **Fix direction:** add `cancelled` (and `queued`) to `AnalysisSummary.status` and `AnalysisResult.status`, and render the terminal state with its failure message.
- **Regression test:** a mapper unit test for all five `AnalysisStatus` values; a backend test already covers cancel (`test_analysis_api.py`).
- **Validation:** static trace.

### [INT-003] Chat discards the backend error (429, 400, 503, 502) and shows a fake "connection failed" answer
- **Severity:** Medium
- **Confidence:** Confirmed
- **Integration area:** Error handling / State
- **Evidence:** `apps/web/lib/api/client.ts:81-86` builds an `Error` with `message = error.message` and `name = error.code`. `apps/web/lib/context/ChatContext.tsx:237` rethrows every code except `CHAT_UNAVAILABLE`, and `:270-292` replaces it with a hard-coded answer: *"An error occurred while connecting…"*, warning *"Inference timeout or connection failed"*, model `error/offline`. Backend: `main.py:186` (429 `RATE_LIMITED` + `Retry-After`), `:194` (400 `VALIDATION_ERROR`), `:206` (503), `:675` (503 `SEARCH_UNAVAILABLE`); proxy `route.ts:24` (400), `:46` (502).
- **Trigger:** send more than 30 chats a minute across all users (see INT-014), or a question over 500 characters.
- **Impact:** a "slow down" or "your question is too long" situation is reported as an outage and suggests the server is down. The fake turn is saved to `localStorage` as if the model had answered. `Retry-After` is forwarded by the proxy but never read.
- **Fix direction:** keep `err.message` and `err.name`, render an error turn (not a `ChatResponse` disguised as a model answer), show the retry delay on `RATE_LIMITED`, and don't persist error turns as answers.
- **Regression test:** mock `fetch` to return 429 `RATE_LIMITED` and 400 `VALIDATION_ERROR`, and assert the turn shows the backend message.
- **Validation:** static trace.

### [INT-004] No client-side limit matching `ChatBody.query` max 500
- **Severity:** Low
- **Confidence:** Confirmed
- **Integration area:** Request DTO
- **Evidence:** `apps/web/app/chat/page.tsx:66` prefills `?q=` sliced to **1000** characters, and the input has no `maxLength`. Backend `main.py:696` (`max_length=500`); contract `ChatRequest.query.maxLength = 500`. The proxy accepts up to 4096 characters of body (`route.ts:23`).
- **Trigger:** paste or link a 600-character question.
- **Impact:** a 400, which INT-003 then turns into "connection failed".
- **Fix direction:** add `maxLength={500}` with a counter, slice the prefill to 500, and trim before measuring.
- **Regression test:** an E2E test that types 501 characters and asserts input is blocked or a clear message appears.
- **Validation:** static trace.

### [INT-005] Read errors are swallowed into "not found" or empty states
- **Severity:** Medium
- **Confidence:** Confirmed
- **Integration area:** Error handling / Resilience
- **Evidence:** catch-all `return null` / `[]` in `apps/web/lib/api/client.ts:133` (`fetchEvidence`), `:179` (`fetchAnalysis`), `:202` (`fetchAnalysesHistory`), `:222` (`fetchExperiments`); `getJson` (`:22`) keeps only `API ${status}`. `apps/web/app/evidence/page.tsx:78` shows *"Evidence record not found."* Backend distinguishes 401 (`main.py:154`), 403 (`:150`), 429 (`:186`), 503 (`:206`), 404 (`:380`). `fireSafety.ts:153-179` handles the same envelope correctly through `ApiError`.
- **Trigger:** a wrong `FLAME_READ_API_TOKEN` on the web server (401), Redis or Postgres down (503), or a rate-limit burst (429).
- **Impact:** operators see "no analyses yet", "not found" or an empty experiments list. That looks like missing data, not a broken deployment, and it misleads both demos and debugging. One failed detail call in `fetchExperiments`'s `Promise.all` empties the whole list.
- **Fix direction:** reuse `fireSafety.ts`'s `get<T>()` / `ApiError` in `client.ts`, return 404 → null only for `*_NOT_FOUND`, and surface other errors through an error state.
- **Regression test:** for each fetcher, mock 401, 429, 503 and 404 and assert that only 404 yields "not found".
- **Validation:** static trace.

### [INT-006] Knowledge-graph API exists but the dashboard is not wired to it
- **Severity:** Low
- **Confidence:** Confirmed
- **Integration area:** Route / Configuration
- **Evidence:** `apps/web/lib/api/client.ts:184-188` returns `[]`, with a stale comment saying no graph API exists. The proxy allowlist (`route.ts:3`) excludes `graph/…`. Backend `apps/api/flame_api/graph.py:62` (`GET /api/graph/entities`) and `:96` (`/{entity_id}`); both are in `docs/api/openapi.json` 0.7.0.
- **Impact:** the Knowledge page is always empty, although the backend serves graph entities.
- **Fix direction:** allowlist `graph/entities(/<id>)?`, map `GraphEntity` to `KnowledgeEntity` using the contract's `GraphReviewStatus` (not a `"verified"` literal, to avoid repeating INT-001), and update the comment.
- **Regression test:** a proxy allowlist unit test, and a mapper test against a `GraphEntity` fixture.
- **Validation:** static trace.

### [INT-007] `conversation_id` is sent but ignored, so follow-up questions have no context
- **Severity:** Low
- **Confidence:** Confirmed
- **Integration area:** Business rules
- **Evidence:** `apps/web/lib/context/ChatContext.tsx:196-199` sends `conversation_id`. Backend `main.py:697` accepts it, but `chat()` (`:773-887`) never reads it and always returns `memory_used: false`.
- **Impact:** the UI looks like a multi-turn conversation, but each question is answered on its own, so "and for methanol?" is retrieved without the earlier topic.
- **Fix direction:** either state "each question is answered independently" in the UI, or implement server-side history (a separate feature).
- **Regression test:** a contract test asserting `memory_used: false`, plus a UI copy check.
- **Validation:** static trace.

### [INT-008] Experiments page lists experiments through a keyword search plus N detail calls
- **Severity:** Low
- **Confidence:** Likely
- **Integration area:** Route / Resilience
- **Evidence:** `apps/web/lib/api/client.ts:207-225` searches `q=flame&type=experiment`, then makes up to 20 parallel `GET /api/experiments/{id}` calls. `GET /api/experiments` (`main.py:952`, paginated) exists and is allowlisted.
- **Impact:** only experiments whose text matches "flame" appear. One page view costs 21 read requests from the shared bucket (INT-014). One failure empties the list (INT-005). "Likely", because which experiments the search misses depends on the corpus.
- **Fix direction:** use `GET /api/experiments` (or add a `conditions` include) and paginate.
- **Regression test:** seed an experiment without "flame" in its text and assert it is listed.
- **Validation:** static trace.

### [INT-009] TypeScript types drift from the contract and nothing checks them
- **Severity:** Low
- **Confidence:** Confirmed
- **Integration area:** Response DTO / Configuration
- **Evidence:**
  - `types.ts:67`: `locator.page?: string`, but the backend sends an int (`main.py:623`).
  - `types.ts:56`: `result_type` includes `"entity"`, which is never produced.
  - `types.ts:72`: `kind` uses observation classes, but the backend sends `EvidenceKind` (`document_passage`, `experiment_condition`, …).
  - `evidence/page.tsx:95`: `.replace("_", " ")` replaces only the first underscore.
  - `client.ts:18`: `Json = Record<string, any>` disables checking.
  - Only `fireSafety.ts` declares response types close to the contract.
- **Impact:** the class of bug behind INT-001 and INT-002 can reach `main` with `tsc` green.
- **Fix direction:** generate TS types from `docs/api/openapi.json` (for example with `openapi-typescript`) and type `getJson<T>`.
- **Regression test:** a CI step that regenerates the types and fails on diff; `tsc` then catches enum drift.
- **Validation:** `tsc --noEmit` passes today, which shows it gives no protection here.

### [INT-010] Analysis studio picks the latest image from only the 20 newest completed analyses
- **Severity:** Low
- **Confidence:** Confirmed
- **Integration area:** Route
- **Evidence:** `apps/web/lib/api/client.ts:161-162`; `GET /api/analyses` has no `analysis_type` filter (`analysis.py:339-349`).
- **Trigger:** 20 or more video analyses completed after the last image analysis.
- **Impact:** the studio shows "no analysis" although image analyses exist.
- **Fix direction:** add an `analysis_type` query filter to the backend and contract, and use it.
- **Regression test:** an API test for the filter, and a mapper test.
- **Validation:** static trace.

### [INT-011] `NEXT_PUBLIC_API_URL` can silently bypass the auth proxy
- **Severity:** Informational
- **Confidence:** Confirmed
- **Integration area:** Configuration / Auth
- **Evidence:** `client.ts:16`, `fireSafety.ts:3` and `VideoAnalysisPanel.tsx:7` prefix every call with `NEXT_PUBLIC_API_URL`. `apps/web/README.md:44` says to leave it unset. FastAPI has no `CORSMiddleware` (`main.py`).
- **Impact:** if someone sets it to the API origin, every browser call goes cross-origin without a token. The result is CORS failures and 401s, and the INT-005 swallowing makes that look like empty data. No token leaks, because the token is never in browser code.
- **Fix direction:** remove the variable, or only allow a same-origin path prefix.
- **Validation:** static trace.

### [INT-012] Contract 0.7.0 `result.audio` (video transcript) is not shown
- **Severity:** Informational
- **Confidence:** Confirmed
- **Integration area:** Response DTO
- **Evidence:** `docs/api/CHANGELOG.md` 0.7.0; `VideoAnalysisPanel.tsx:10-28` has no `audio` field.
- **Impact:** a feature gap only. The field is optional and off by default, so nothing breaks.
- **Validation:** static trace.

### [INT-013] Stray `apps/web/apps/web/package-lock.json`
- **Severity:** Informational
- **Confidence:** Confirmed
- **Integration area:** Configuration
- **Evidence:** an untracked nested folder holding only a lockfile, most likely an `npm install` run from the wrong directory.
- **Fix direction:** delete it after checking nothing references it.
- **Validation:** `find apps/web/apps -type f`.

### [INT-014] All dashboard users share one API identity, so one user can exhaust everyone's rate limit
- **Severity:** Medium
- **Confidence:** Confirmed
- **Integration area:** Auth / Resilience
- **Evidence:** the proxy sends one `FLAME_READ_API_TOKEN` for every browser (`route.ts:28-29`, `:68-69`) and forwards no client identity. The backend rate-limits per identity (`main.py:116-117`, `:178`). Defaults are `chat_rate_limit_per_minute=30` and `read=600` (`config.py:72-74`). The Next.js handler has no throttle of its own.
- **Trigger:** one visitor scripts 30 `POST /api/chat` calls a minute.
- **Impact:** chat returns 429 for every user, shown as "connection failed" (INT-003). Read pages hit the same limit at 600 requests a minute; the experiments page alone costs 21 per view (INT-008). Anyone who can reach the web app also gets unauthenticated read and chat access, by design for a public dashboard.
- **Fix direction:** add a per-IP limiter in the Next.js handler (or at the edge), and/or forward a hashed client IP for the backend to key a second bucket on.
- **Regression test:** a proxy test that sends N+1 chats from one IP, asserts that IP gets 429, and asserts a second IP still succeeds.
- **Validation:** static trace; the backend limiter itself is covered by existing tests.

---

## 5. End-to-end workflow results

| Workflow | Trace | Result |
|---|---|---|
| **Ask a cited question** | `chat/page.tsx:55` (no empty send ✓; `isSending` blocks double submit ✓) → `ChatContext.sendMessage` (optimistic loading turn) → `submitChat` → proxy POST (read token, 130 s) → `_authorized` (read scope, chat bucket) → `ChatBody` validation → cache lookup → `_retrieve_passages` → `answer_question` → `sources` → UI links `/evidence?id=` | **Pass** on the happy path, including the backend's own degraded `generation_unavailable` answer and the frontend's `CHAT_UNAVAILABLE` → search fallback. **Fail** on 400, 429 and 5xx (INT-003, INT-004). No context carries between turns (INT-007). |
| **Open an evidence record** | chat or search source link → `fetchEvidence` (regex, then the proxy regex, then the backend ULID pattern) → `get_evidence` → map | **Fail**: wrong review badge (INT-001); errors read as "not found" (INT-005). |
| **Fire-safety dashboard (scenario → investigations → detail → insights → FLEX)** | `fireSafety.ts` typed calls → `investigations.py` with `_scenario` (both custom values or neither) → `ApiError` with `field_errors` | **Pass.** This is the best-integrated area: shapes match, errors are surfaced, validation messages are shown. |
| **Analysis history / studio** | `fetchAnalysesHistory` / `fetchAnalysis` → `GET /api/analyses` → `GET /api/analyses/{id}` → artifacts through the proxy | **Fail** for cancelled jobs (INT-002) and for image selection after many videos (INT-010). **Pass** otherwise. |
| **Video analysis panel** | `VideoAnalysisPanel` → list (completed, 50) → detail → `result.temporal_summary` | **Pass**; audio is not shown (INT-012). |
| **System status** | `fetchHealth` reads the body even on 503 → maps statuses | **Pass.** |
| **Upload or cancel an analysis from the UI** | no UI caller; the proxy blocks POSTs other than chat | **Not applicable**: by design, done with the write key (`DEMO_RUNBOOK.md`). |

---

## 6. Authentication and authorization review

- **The token never reaches the browser.** `FLAME_READ_API_TOKEN` is read only inside the route handler (`route.ts:28`, `:68`), and no client file reads it. ✓
- **Least privilege.** The web service holds only a read key. Chat is deliberately read scope (`main.py:103-106`). Write and admin routes are unreachable through the proxy (GET allowlist, and POST only for `chat`), and the backend enforces scope again in middleware plus `require_admin_scope` (`admin.py:38`). ✓
- **401 vs 403.** The backend separates them correctly (`main.py:150`, `:154`). The frontend does not: `client.ts` folds both into empty or not-found states (INT-005); `fireSafety.ts` shows a generic message.
- **Object-level access.** All exposed data is a shared public corpus with no per-user ownership, so IDOR does not apply. There is no user login in the dashboard.
- **Rate-limit identity** is shared (INT-014).
- **Path injection through the proxy.** `joined` is checked against an anchored regex before use, and the query string is passed through. Backend handlers validate their own query parameters. No traversal path was found. ✓
- **Secrets in logs.** The backend logs `client=<identity name>`, never the token (`main.py:89`). ✓

## 7. Data and business-rule consistency

- **Validation agreement:** the scenario rule, the FLEX ranges and the sum ≤ 1 rule agree, because the frontend sends and the backend enforces; the frontend shows `field_errors`. The chat length limit disagrees (INT-004). The search `page_size` is within backend limits at every call site (20 ≤ 50).
- **Enum agreement:** `ServiceStatus`, `OverallStatus`, `InsightKind` and the fire-safety `status` agree. `ReviewStatus`, `AnalysisStatus` and `EvidenceKind` do not (INT-001, INT-002, INT-009).
- **Timestamps:** the backend always emits UTC with a `Z` suffix (`_timestamp`, `_utc`). The frontend passes them to `Date` / `toLocale*`, so they are compatible.
- **Caching:** API reads use `cache: "no-store"` on both hops. Artifacts are immutable and cacheable by sha256 ETag, which is correct because artifacts are content-addressed.

## 8. Validation evidence

All commands were run on 2026-11-13 from `E:\Nasa\Nasa`, locally, with no network calls to any deployed API.

| Command | Result |
|---|---|
| `cd apps/web && npx tsc --noEmit` | **pass**, no output |
| `cd apps/web && npx eslint lib app components` | **pass**, no output |
| `python -m pytest apps/api/tests -q -x` (full suite) | stopped at the 500 s timeout, about 35% through, **no failures before the cutoff**; not a full result |
| `python -m pytest` on `test_contract_parity, test_read_api, test_chat, test_fire_safety_api, test_health, test_list_api, test_analysis_api, test_auth_config, test_api_clients` | **pass**: 91 collected, 90 passed, 1 skipped, exit 0. `test_fire_safety_api` setup takes about 90 s per test. These tests confirm backend behaviour against the contract; they do not exercise the frontend mappers. |
| OpenAPI enum inspection (`docs/api/openapi.json`: `ReviewStatus`, `AnalysisStatus`, `EvidenceKind`, `ChatRequest`) | confirmed the backend side of INT-001, INT-002, INT-004 and INT-009 |

**Limitations:**
- No frontend tests exist (there is no test runner in `apps/web/package.json`), so nothing in CI exercises the mapping layer.
- The stack was not run; proxy timeouts and stream forwarding are verified by reading only.

## 9. Coverage gaps and unverified risks

- **Not inspected in depth:** search ranking internals, the ingest pipeline, the worker's video payload beyond the fields the panel reads, the admin routes (not used by the UI), and `/api/documents*` (no UI caller).
- **Unverified at runtime:**
  - streaming a large artifact through `new Response(upstream.body)` on the deployed Node runtime;
  - behaviour when the backend takes longer than 20 s on a GET (the proxy returns 502 `UPSTREAM_UNAVAILABLE`, which `client.ts` swallows);
  - SSR or prerender of the client pages with `FLAME_API_ORIGIN` unset.
- `mockData.ts` exists but no fetcher imports it. That was not checked further.

## 10. Prioritized remediation plan

| Priority | Item | Findings | Depends on | Regression test |
|---|---|---|---|---|
| **P0** | Fix the enum mappers for review status and analysis status | INT-001, INT-002 | – | mapper unit tests over every contract enum value |
| **P0** | Surface chat errors honestly, and stop persisting fake answers | INT-003, INT-004 | – | mocked 429/400 chat tests |
| **P1** | Typed `get<T>` with `ApiError` in `client.ts`; 404 is the only "not found" | INT-005 | – | fetcher error-matrix tests |
| **P1** | Per-IP throttle in the Next.js handler | INT-014 | – | proxy rate-limit test |
| **P1** | Generate TS types from `docs/api/openapi.json`, and add a vitest runner to `apps/web` | INT-009 | adding a test runner | CI diff check, then `tsc` |
| **P2** | Wire `/api/graph/entities` | INT-006 | P1 types | allowlist + mapper tests |
| **P2** | Use `/api/experiments` for listing; add `analysis_type` filter | INT-008, INT-010 | backend + contract change for the filter | API + UI tests |
| **P2** | Single-turn chat copy, or real history | INT-007 | product decision | UI copy check |
| **P2** | Remove `NEXT_PUBLIC_API_URL`; delete the stray lockfile; render `audio` | INT-011, INT-012, INT-013 | – | – |

## 11. Suggested contract tests

1. **Enum parity test (Python, in `test_contract_parity.py`'s style).** Load `docs/api/openapi.json` and assert that every value of `ReviewStatus`, `AnalysisStatus` and `EvidenceKind` appears in a checked-in `apps/web/lib/api/contract-enums.json`. Have the frontend import that file. A backend enum change then fails CI until the frontend is updated.
2. **Proxy allowlist test (TS).** For each `GET` path in the contract, assert whether `ALLOWED` matches it against an explicit expected list. Write and admin paths must never match.
3. **Chat error passthrough (TS, mocked fetch).** For 429 `RATE_LIMITED`, the turn shows the backend message and `Retry-After`. For 400 `VALIDATION_ERROR`, it shows the length message.
4. **Mapper golden tests (TS).** Run `fetchEvidence`, `fetchAnalysis` and `fetchAnalysesHistory` against JSON fixtures captured from `apps/api/tests` responses (human-verified evidence, a cancelled analysis), and assert the UI model.
5. **Shared-bucket test (Python + proxy).** Two simulated browser IPs: exhausting one must not 429 the other once the per-IP limit exists.

---

## Top 5 next actions

1. Fix the `review_status` and analysis `status` mappers to the contract enums (**INT-001, INT-002**).
2. Make chat show the backend's error code, message and retry delay, and cap input at 500 characters (**INT-003, INT-004**).
3. Replace the catch-all `return null` / `[]` in `client.ts` with `ApiError` handling, so 401, 429 and 503 are visible (**INT-005**).
4. Add a per-IP throttle in `app/api/[...path]/route.ts` (**INT-014**).
5. Add a frontend test runner and contract-generated types, so enum drift fails CI (**INT-009**, coverage gap §8).
