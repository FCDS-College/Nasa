# Required Updates: Belal (Engineer 4, Frontend / Visualization)

| | |
|---|---|
| **Reviewed** | branch `create-front` @ `f6823c2` ("feat(frontend): update NASA frontend", 2026-10-14), 24 files, +2319 / −200 |
| **Reviewed by** | Lead (Anas), 2026-10-18 |
| **Basis** | `docs/api/FRONTEND_API_CONTRACT.md`, Phase 2 Plan (M7, §13 scientific UI rules), `DOC_REQUIREMENTS_Belal.md` (on branch `Belal`) |
| **Checks run** | `tsc --noEmit` **pass**, `eslint .` **pass**, `tsx --test tests/*.test.ts` **13/13 pass**. A trial merge into `main` gives **7 conflicts**. |

## Verdict: 5 / 10, not mergeable yet

The UI work is good: there are new Dashboard and Documents pages, an expanded Analysis page with contract-correct image validation (PNG/JPEG, ≤ 10 MiB, ≥ 64×64 px), the fonts moved to `next/font`, and you added the first frontend tests. Thank you.

The branch has three blocking problems:
1. It **replaces the hardened API proxy on `main` with an open one**.
2. When the API is down, it **shows invented scientific data as if it were real**.
3. It started 129 commits behind `main` and now **conflicts in 7 files**.

---

## 1. Blocking (must fix before a PR is accepted)

| # | Severity | File | Problem | Required change |
|---|---|---|---|---|
| B1 | **Critical (security)** | `apps/web/app/api/[...path]/route.ts` | It proxies **every path and every method** (GET/POST/PUT/PATCH/DELETE) to the backend and attaches the server bearer token to each request. Any anonymous visitor to the website can then make authenticated write or delete calls on the API. It also forwards all client headers (cookies included) upstream, and passes every upstream response header back. The version on `main` is a strict allow-list: read-only GETs on named paths, plus one `POST /chat` with a 4 KB body cap, timeouts, and only `content-type` / `cache-control` / `retry-after` returned. | Drop your version of this file and keep `main`'s. If you need a new endpoint (e.g. `POST /api/analyses`, `GET /api/documents` list), add it to `main`'s `ALLOWED` pattern or as its own handler. Ask the Lead before anything uses a write token. |
| B2 | **Critical (deploy)** | same file + `lib/api/client.ts` | The env var names are `API_BACKEND_URL` / `NEXT_PUBLIC_API_URL` / `API_READ_TOKEN` / `API_BEARER_TOKEN`. Railway and `main` use `FLAME_API_ORIGIN` and `FLAME_READ_API_TOKEN`, so this branch would deploy with no backend. `NEXT_PUBLIC_API_URL` also invites calling the API straight from the browser. | Use `FLAME_API_ORIGIN` and `FLAME_READ_API_TOKEN` (server-only). The browser always calls same-origin `/api/...`. |
| B3 | **Critical (scientific integrity)** | `lib/api/client.ts` → `submitFlameAnalysis` (catch branch) | If the upload fails to reach the API, the client **makes up a `status: "completed"` CV result**: model `YOLOv8-Flame-v1.1`, flame area 14082 px with `confidence: 0.94`, `observation_type: "measured"`, and a fake `sha256:sim_…` checksum. The "Simulated Result" badge does not make this acceptable: a measurement labelled `measured` that nothing measured is exactly what §13 forbids. | Remove the simulated analysis. On a network failure, show the contract error state (`UPSTREAM_UNAVAILABLE`, retryable) with a Retry button, and create no result. |
| B4 | **Critical (scientific integrity)** | `lib/api/mockData.ts` + `fetchHealth`, `fetchDashboardData`, `searchResearch`, `fetchEvidence`, `fetchDocuments`, `fetchDocument`, `fetchAnalysesHistory`, `fetchExperiments` | Every fetch falls back **silently** to mock data when it fails. With the API down, the UI shows **all 7 subsystems "up"** (including `vLLM-L40S` and `Redis 7.0`, which we don't run), **14,502 documents / 1,250,394 chunks**, and "verified" evidence. This is the Day 1 finding ("hard-coded System Online") again, at a larger scale. | Remove the mock fallbacks from `client.ts`. Each call returns either real data or a typed error, and each page renders **loading / empty / error** states. If a demo mode is really needed, gate it behind an explicit `NEXT_PUBLIC_DEMO_MODE=1` build flag with a permanent banner on every page, and keep it off in production. |
| B5 | **Critical (scientific integrity)** | `app/dashboard/page.tsx` lines ~162-164 | It hard-codes an "evaluation scorecard": RAG Recall@5 **0.92 PASS**, CV IoU **0.88 PASS**, Grounding **0.96 PASS**. None of these were measured. Ziad's generated baseline reports Recall@5 ≈ 0.18-0.21, and CV IoU has not been evaluated at all. | Remove the hard-coded scorecard. Either read it from a generated report/API, or show "Not evaluated yet". The same applies to the `"HEALTHY"` default at line ~117: with no health data, show "Unknown". |
| B6 | High | whole branch | It was branched at `d3fa1f0` (2026-10-07), and `main` is 129 commits ahead. A trial merge conflicts in `analysis/page.tsx`, `api/[...path]/route.ts`, `layout.tsx`, `lib/api/client.ts`, `mockData.ts`, `ChatContext.tsx` and `next.config.ts`. `main` has meanwhile added the real `POST /api/chat` path, the read-only proxy, a Dockerfile, and changes to `ChatContext`. | Start a fresh branch from current `main` (`git switch -c belal/frontend-v2 origin/main`), then port your new pages and tests onto it. Don't merge `main` into `create-front` and resolve by keeping "ours"; that would undo the Lead's fixes. |

## 2. Required (fix in the same PR)

| # | File | Problem | Required change |
|---|---|---|---|
| R1 | `apps/web/tests/*.test.ts` | The tests pass only **because** the fetch fails and the mocks answer. For example, `search-evidence-flow.test.ts` asserts `review_status === "verified"`, and `analysis-flow.test.ts` asserts that the simulated analysis is `"completed"` with `mm²`. They lock in the behaviour B3/B4 forbid. | Stub `global.fetch` in each test, and assert both paths: a success response renders real fields, and a failure returns an error (never mock data). Keep the image-validation tests; they are good. |
| R2 | `lib/api/client.ts` → `submitChat` | The comment says "/api/chat is not yet implemented"; it is on `main`. On failure it returns a delayed fake answer. | Use `main`'s chat flow. On failure, show an error message in the thread, not a fabricated answer. |
| R3 | `lib/api/client.ts` → `fetchKnowledge` | Always returns `mockKnowledge` and never calls the API (M7 open item: "mocked Knowledge page"). | Either call a real endpoint or render an "Not available yet" empty state. |
| R4 | `lib/api/client.ts` | Module-level `localAnalysesStore` / `localHistoryStore`, seeded from `mockHistory`, make invented analyses appear in History and survive navigation. | Remove them. History comes from `GET /api/analyses` only. |
| R5 | `app/api/[...path]/route.ts` (if anything of it survives) | The `DATABASE_UNAVAILABLE` error code is returned when the upstream can't be reached. | Use `UPSTREAM_UNAVAILABLE` (as on `main` and in the contract). |
| R6 | `next.config.ts` | `allowedDevOrigins: ["192.168.2.3", …]` hard-codes your LAN IP. | Remove it, or read it from an env var for local development only. |
| R7 | `package.json` `"test"` | `npx tsx …` downloads `tsx` at run time; it isn't in `devDependencies`, so CI and offline runs fail. | Add `tsx` to `devDependencies` and use `"test": "tsx --test tests/*.test.ts"`. Then add `npm test` to `.github/workflows/ci.yml` (coordinate with the Lead). |
| R8 | `components/layout/Sidebar.tsx` | 10 nav links. Check every target page renders without 404 and has real (or honestly empty) data. | Confirm in the PR description with one screenshot per page, taken against the live API. |

## 3. Documentation

| # | File | Problem | Required change |
|---|---|---|---|
| D1 | `docs/frontend/implementation-summary.md` | It's in Arabic, has no header block, and `DOC_REQUIREMENTS_Belal.md` says it is **replaced** by `docs/frontend/architecture.md` (E4-1). `main` has already deleted the old `apps/web/Documentation/` copy. | Write `docs/frontend/architecture.md` in English with the header block. Cover the proxy (what it forwards, how tokens stay server-side), `client.ts` error handling, the env var names (no values), and **an explicit list of anything still mocked**. |
| D2 | `docs/frontend/screens.md` (E4-2) | Missing. | Add one row per page: route, API calls, states handled (loading/empty/error), and owner. |
| D3 | `docs/frontend/testing.md` (E4-6) | Missing. | How to run `npm test`, what is stubbed, and what CI runs. |

## 4. What was good (keep it)
- `validateImageFile`: contract-correct type, size and dimension checks, with clear user messages.
- The new **Documents** and **Dashboard** layouts, and the expanded **Analysis** workflow UI (calibration inputs, measurement table with units and observation type).
- Fonts moved to `next/font`, which removes the external stylesheet request.
- Types added in `lib/api/types.ts` for documents, experiments and the error envelope.
- Typecheck and lint are clean.

## 5. Acceptance checklist (the Lead checks this before approving the PR)
- [ ] A new branch from current `main`; no merge conflicts; `main`'s proxy route unchanged, or only extended through its allow-list.
- [ ] No production code path returns mock, simulated or hard-coded scientific values. A search for `mockData` in `lib/api/client.ts` finds nothing, or only code behind `NEXT_PUBLIC_DEMO_MODE`.
- [ ] Every page shows correct loading, empty and error states with the API stopped (screenshots attached).
- [ ] Every page shows real data with the API running (screenshots attached).
- [ ] `npm run typecheck`, `npm run lint` and `npm test` pass locally and in CI; the tests stub `fetch`.
- [ ] `docs/frontend/architecture.md`, `screens.md` and `testing.md` exist in English with the header block.
