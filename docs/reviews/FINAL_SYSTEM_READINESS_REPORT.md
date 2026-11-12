# Final system readiness report (2026-10-30)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas), assessment by Claude Code | Historical snapshot (2026-10-30), with a status update | 1.1.0 | 2026-11-12 | release gate input | whole repository |

> Sections 1–10 are the assessment as written on 2026-10-30 and are not edited. [§11](#11-status-update-2026-11-12) records what has changed since, item by item. For the current state of the project, read [FINAL_PROJECT_STATUS.md](../../FINAL_PROJECT_STATUS.md).

## 1. Summary

The code is in better shape than its CI status suggested. Every core workflow that the environment allowed ran end to end on a live stack: search, evidence, image CV, video CV, offline chat, outage recovery and the audited mode switch. CI on `main` was red, there were two vulnerable dependencies (one critical) and the AURA error handling had two integration defects. Those are fixed on this branch, and video analysis is now exposed through the API.

The system is **not production-ready**, for three reasons:
- model evaluation does not yet measure Flame;
- deployment has not been dry-run on a container host;
- no test has used a deployed AURA.

Each needs something this environment lacks: human annotation, Docker, or AURA credentials.

Levels of completion are kept separate throughout this report:

| Level | Meaning here |
|---|---|
| Code complete | implemented on the branch |
| Tests passed | `python -m pytest` and the web checks |
| Integration verified | contract-level: AURA dry run plus AURA's tests; and HTTP-level: the same calls against the live Flame stack |
| Runtime verified | exercised on Postgres+pgvector, Redis, S3 stand-in, uvicorn, RQ worker, Next.js, llama.cpp |
| Production verified | **none**. Nothing was deployed. |

## 2. Before / after

| Area | Before (`7340782`) | After (this branch) |
|---|---|---|
| CI (`ruff`, `pytest`) | red: 23 lint errors, collection error | green: 0 lint errors, 309 passed / 6 skipped |
| Web dependencies | `next` 16.3.8, 1 critical advisory | 16.4.3, 0 advisories |
| Image decoding | Pillow 12.3.0, 39 CVEs | Pillow 13.x |
| Video analysis via API / AURA | missing | `flame_video`, runtime-verified on NASA BASS video |
| AURA schema-failure fallback | none (`INVALID_REQUEST`) | falls back (`INVALID_OUTPUT`) |
| AURA idempotency replay / reuse | stale failures replayed; new evidence rejected | body-bound key; context capped at 2000 |
| Contract version reported | `meta.api_version` 0.1.0 ≠ contract 0.2.0 | 0.3.0 = contract, test-pinned |
| Dashboard Knowledge page | invented "verified" entities | honest "not available" |
| Interpretation crash | could fail a completed analysis | isolated |

## 3. Final architecture

```
Browser ─▶ Next.js 16 (apps/web) ─ server-side proxy (read token, GET + chat only) ─┐
AURA agent (Link 2, read token, 10 GET tools) ───────────────────────────────────────┤
                                                                                     ▼
                      FastAPI (apps/api, contract docs/api/openapi.json 0.3.0, bearer auth)
                       │  search: Postgres FTS + pgvector (RRF)   chat: Flame retrieval → router
                       │  analyses: image/video → S3 original → RQ queue
                       ▼
     PostgreSQL+pgvector · Redis/RQ · S3/MinIO          RQ worker (apps/api/flame_api/worker.py)
                       │                                       │
                       └──────── ai/routing Router (modes: cloud_preferred · local_first · offline_only)
                                  ├ text: vLLM (GPU) → Ollama (CPU) → llama.cpp → AURA (external, Link 1, optional)
                                  ├ embeddings: FastEmbed bge-small (local)   rerank: cross-encoder (optional)
                                  └ vision: flame_cv (local) / HF Space (external)   video: flame_cv_video (local only)
```

## 4. Readiness by area

| Area | Status | Basis |
|---|---|---|
| Integration with AURA | **Contract-ready; deployment untested** | Dry run vs AURA HEAD: 10 tools accepted, 3 excluded. AURA's integration tests: 251 passed. Link 1 defects fixed. Flame GETs verified with auth. AURA A1–A4 merged (AURA-AI #200) and the CI pin moved to `d696fad` (A5). Open: a staging run (P1-8), per-client tokens before public exposure (P2-1). |
| AI / RAG | **Functional, quality unmeasured** | Hybrid retrieval with evidence IDs and locators; grounded chat with citation filtering; CAG works. No valid evaluation (P1-6); `ai/rag` reranker and memory not wired in (ADR-006). |
| CV (image) | **Functional, heuristic** | Runtime-verified; scientific labelling correct; detector unvalidated against labels. |
| CV (video) | **Functional (new), heuristic** | Runtime-verified on a 1343-frame NASA clip; time order, Nyquist and tracking-gap guards. |
| Offline | **Verified on a live stack** | See §5. |
| Security | **Acceptable for a closed deployment** | Critical dependencies fixed; strong upload validation; secrets server-side. Open: shared static tokens, chat-only rate limit, non-production defaults accepted in production (P2-1, P2-2, P2-6). |
| Data management / admin | **Operator-only** | CLI pipelines are idempotent and audited where noted; no admin endpoints or UI (P2-8). |
| Deployment | **Unverified** | No Docker daemon available; compose not run (P1-7). |

## 5. Offline readiness

Run with `FLAME_AI_EXECUTION_MODE=offline_only`, `FLAME_EMBEDDING_OFFLINE=true`, AURA disabled, and a local llama.cpp server holding Qwen2.5-0.5B-Instruct Q4_K_M:
- `/api/health`: `llm: up (llamacpp:local)`, `aura: disabled`, mode `offline_only`.
- Chat was answered by `llamacpp` (locality `local`), citing page 1 of the NTRS report, in 21 s on CPU. The second ask was a cache hit.
- Image and video CV ran locally (`flame_cv`, `flame_cv_video`). Query embeddings came from the local FastEmbed cache.

**Caveat (shim).** Flame's `llamacpp` provider targets upstream llama.cpp `llama-server`, which accepts `response_format: {type: json_schema}`. Only the `llama-cpp-python` server could be installed here, and it accepts only `json_object`. Building upstream llama.cpp was not permitted in this environment. A 30-line test-only proxy rewrote that single field; every other byte, including the model's output and Flame's validation, was unmodified. Re-run this step against `llama-server` or Ollama before calling the offline path production-verified.

**Quality.** The 0.5B model's answer was grounded and correctly cited but weakly relevant. Use the documented default, `qwen2.5:3b-instruct-q4_K_M` via Ollama (`docker-compose` `x-ai-env`), or larger. Minimum hardware for a 3B Q4 model on CPU is about 4 GB free RAM and 4 cores, at roughly 5–10 tokens/s, which is why `FLAME_LLM_TIMEOUT_S` defaults to 180 s. A 7B AWQ model on vLLM needs a GPU with at least 8 GB.

**Recovery.** With the local model stopped, chat degraded to evidence only (`generation_unavailable`, no generated text) and health went `degraded`. After the model restarted, routing recovered by itself within about 30 s (health TTL 15 s plus circuit cooldown 30 s), with no API restart.

## 6. End-to-end workflows

| WF | Initial conditions | Execution | Expected | Actual | Result |
|---|---|---|---|---|---|
| A. Document processing | 3 NTRS PDFs committed | `seed` → `ingest` → `vector_index build` → `/api/search` → `/api/evidence/{id}` → `/api/chat` | chunks with page evidence, hybrid hits, cited answer | 37 chunks, 37 embedded, `mode: hybrid`, page locators, evidence excerpt; chat cites `p. 1` | **PASS (CLI ingestion)**. There is no upload API: ingestion is operator-run by design. |
| B. Experiment | PSI tables not installed (git-ignored, ~6 GB) | — | experiments with conditions | 0 experiments in this environment | **NOT RUN**. Unblock: `python knowledge/ingestion/install_datasets.py --skip-large && python -m flame_api.ingest` |
| C. Video analysis | NASA BASS clip `FF-PSI-25` (H.264, 1343 frames) | upload → probe → queue → worker → GET | time-ordered frames, temporal summary, evidence | 40 frames, persistence 1.0, flicker not estimable (Nyquist), tracking not estimable at 1 s (and 2 sessions at 0.17 s), `video_measurement` evidence | **PASS** |
| D. Research via AURA | AURA not deployed here | dry run (contract) + the same GETs with the read token | tools compile; calls succeed | 10 tools ACCEPTED; GETs return 200; 401 without a token | **PARTIAL**: contract and HTTP verified; the live AURA agent was not run (P1-8) |
| E. Offline AI | `offline_only`, local llama.cpp | `/api/chat` | local model answer with provenance | `llamacpp`/`local`, cited, 21 s | **PASS** (with the shim caveat in §5) |
| F. Recovery | local model killed, then restarted | `/api/chat` before and after | degrade, then recover without restart | evidence-only → `llamacpp` after ~30 s; health degraded → healthy | **PASS** |
| G. Dashboard and admin | live API + `next start` proxy | health, counts, analyses list via proxy; `PUT /api/admin/ai/mode` with read and write tokens | real counts; read token refused; mode change audited | counts from persisted rows (2 analyses); read token → 401; `audit_event` before/after rows; admin routes 404 through the proxy | **PASS** for health, counts and mode. Data management: **MISSING** (P2-8). |
| — Image analysis | NASA ISS and SAFFIRE frames | upload → worker → GET | 4 artifacts, evidence, no temperature | `completed`, original/preprocessed/mask/overlay, `TEMPERATURE_NOT_AVAILABLE` | **PASS** (also re-run on Pillow 13) |

Logs from these runs were kept in the session's scratch area; they are not committed.

## 7. Test and build results

| Check | Result |
|---|---|
| `ruff check .` | All checks passed |
| `python -m pytest` (repo root) | **309 passed, 6 skipped**. The skips are 4 stale eval stubs that still say "API backend implementation is pending", plus the missing PSI mirror and tesseract. |
| `render_api_schemas.py --check`, `validate_registry.py` | current; 0 problems |
| Web `npm run lint` / `typecheck` / `build` | 0 errors (5 pre-existing unused-import warnings) / clean / OK |
| `npm audit --omit=dev` | 0 vulnerabilities |
| Alembic up → down → up on pgvector | OK |
| AURA dry run (HEAD `6417c43`, contract 0.3.0) | 10 accepted, 3 excluded, exit 0 |
| AURA integration-related tests | 251 passed, 2 skipped |
| Docker compose, gitleaks | not run (no Docker daemon; the gitleaks binary download was not permitted). CI runs gitleaks. |

## 8. Deployment readiness

**Not ready for production; ready for a staging deployment.** Before production:
1. Compose dry run on a clean host (P1-7).
2. Per-client tokens and per-key rate limits, if AURA is reached over the public internet (P2-1, P2-2).
3. Refuse default secrets in production (P2-6).
4. Backup and restore drill (P2-11).
5. Valid evaluation numbers before any quality claims (P1-6).

## 9. Remaining blockers and exact unblock actions

| Blocker | Needed | Action |
|---|---|---|
| Deployment unverified | A host with Docker | `cd infrastructure && cp .env.example .env` (set two 32+ char tokens), `docker compose up -d`, then repeat §6 |
| Live AURA test | AURA SuperAdmin; a reachable Flame URL over https | Register the Flame OpenAPI connector with the read token; issue a `svc-flame` key → `FLAME_AURA_ENABLED=true`, `FLAME_AURA_SERVICE_TOKEN` |
| Evaluation | Domain annotators | Re-annotate `datasets/evaluation/rag_gold.jsonl` against the registered corpus (P1-6) |
| Experiments workflow | Network + ~6 GB disk | `python knowledge/ingestion/install_datasets.py --skip-large`, then `python -m flame_api.ingest` |
| Offline path on the real runtime | `llama-server` or Ollama | Run §5 without the shim |

## 10. Recommended next priorities

1. Merge this branch so CI goes green and the critical dependency fixes ship.
2. Run the compose dry run, then the AURA staging test (P1-7, P1-8).
3. ~~Ask AURA for changes A1–A4 and bump the pinned AURA revision~~ Done 2026-10-30: AURA-AI #200, pin `d696fad`.
4. Re-annotate the gold set and run real evaluation; rank models only from recorded runs (P1-6).
5. Per-client tokens and rate limiting (P2-1, P2-2), then stuck-job recovery (P2-4).

No overall completion percentage is given: the requirement set has no agreed weights, and a single number would hide the difference between "code complete" and "verified".

## 11. Status update (2026-11-12)

What changed after this assessment, for each finding above. Evidence is in [FINAL_TEST_REPORT.md](../../FINAL_TEST_REPORT.md) (FTR) and the status table of [IMPLEMENTATION_ROADMAP.md](../plan/IMPLEMENTATION_ROADMAP.md).

| Finding on 2026-10-30 | Now | Evidence |
|---|---|---|
| Dashboard Knowledge page showed an honest "not available" (§2) | **Built.** The Knowledge Graph page (`/knowledge`) browses the real graph: 951 entities and 10,683 edges, each citing the NASA table cell it was read from. You can walk links 1 or 2 hops and open each link's evidence. | PR #32; FTR §10: smoke test 9/9 steps, iPhone 13 no overflow; CI green |
| WF B, Experiment: **NOT RUN**, PSI tables not installed (§6, §9) | **Runs on a fresh clone.** The small CC0 PSI tables are committed (ADR-012). Ingest gives 840 flight tests from FLEX, BASS-II, SPICE and SAFFIRE-I. | FTR: migrate → seed → ingest |
| AI / RAG: quality unmeasured; the `ai/rag` reranker not wired in (§4) | **Retrieval measured; generation still not.** One `ai/rag` search stack (ADR-006), with the cross-encoder reranker on by default. On the 26-question gold set: hit@1 0.88, MRR@10 0.91, recall@5 0.88. The gold set was written with AI assistance and is not yet human-reviewed (P1-6 still open). No language model was available to evaluate generated answers. | [retrieval-2026-11-12.md](../evaluation/reports/retrieval-2026-11-12.md); FTR §9 |
| AURA: contract 0.3.0, 10 tools accepted, 3 excluded; no live AURA test (§4, WF D) | **Contract 0.6.0:** 16 tools accepted, 10 operations excluded, against AURA `d696fad`. AURA's own runbook matches (AURA-AI #232). **A live AURA agent has still not been run (P1-8 open).** | FTR §8–§9 |
| Security: shared static tokens, chat-only rate limit, default secrets accepted in production (P2-1, P2-2, P2-6) | **Fixed:** per-client hashed keys with `read`, `write` and `admin` scopes, and every admin key must name an owner (ADR-009). Per-key Redis rate limits on all routes. Production start-up refuses default secrets. Still true: owners are free text, not verified identities, and the deprecated write token remains an admin credential. | Roadmap P2-1, P2-2, P2-6; SECURITY.md 0.7.0 |
| Data management: no admin endpoints or UI (P2-8, WF G) | **Audited admin endpoints** for reprocessing, review status and quarantine, behind the `admin` scope. Still **no admin UI**: the web tier never holds a write key. | Roadmap P2-8 |
| Stuck jobs after a worker crash (P2-4) | **Fixed:** `worker recover` runs at worker start. Video jobs now checkpoint every 10 frames and resume with a frame-for-frame identical result. They can also be cancelled (ADR-008). | Roadmap P2-4; FTR §8 |
| Backup and restore drill (P2-11) | **Local drill done** (21/21 tables, 8/8 objects matched). There is no schedule, and the Compose/MinIO drill is still pending. | Roadmap P2-11 |
| Deployment unverified (P1-7) | **Still unverified.** There was no Docker host and no Railway access, so the compose dry run has not been done. | FINAL_PROJECT_STATUS §3 |
| Offline path verified only through a test shim (§5) | **Unchanged.** It has not been re-run against `llama-server` or Ollama. | — |
| Tests: 309 passed; web lint 5 warnings; gitleaks not run (§7) | 423 passed, 6 skipped. Web lint has 0 warnings. gitleaks runs in CI on every PR (green on PR #32). | FTR §9, §10 |

**The deployment verdict in §8 stands: not production-ready.** Of its five pre-production items, three are done or partly done:
- per-client tokens and rate limits;
- the refusal of default secrets;
- a local restore drill.

Two remain open:
- the compose dry run (P1-7);
- valid evaluation numbers. Retrieval has numbers, but the gold set is not human-reviewed, and generation is unmeasured.

## Changelog
- 1.0.0 (2026-10-30): the readiness assessment.
- 1.1.0 (2026-11-12): §11 status update. Marked as a historical snapshot; sections 1–10 are unchanged.
