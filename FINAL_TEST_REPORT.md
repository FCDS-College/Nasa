# Final test report: Flame in Freefall

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas), run by Claude Code | Current | 1.1.0 | 2026-11-12 | T7, ADR-006–009 | whole repository |

Every result below was produced by a command run on 2026-11-07 on branch `anas/vibrant-sagan-fsnckf`. "Not run" means it was not run.

## 1. Environment

- Python 3.13 venv with `apps/api[dev,cv,ingestion,ocr,vector]`, `ai/requirements.txt` and CPU PyTorch; Node 22.
- A local live stack: PostgreSQL 16.15 + pgvector, Redis 7, a `moto` S3 stand-in, uvicorn with **auth enabled** (random 48-character read and write keys), an RQ worker, `next start`, and Tesseract.
- No Docker daemon was available.
- No language model ran: an attempt to start Ollama was declined by the session's permission policy.

## 2. Static checks and unit/integration tests

| Check | Command | Result |
|---|---|---|
| Python lint | `ruff check .` | All checks passed |
| Full test suite (repo root) | `python -m pytest` | **385 passed, 5 skipped, 0 failed** (baseline before this work: 365 passed, 7 skipped) |
| Skips | `python -m pytest -rs` | OpenTelemetry SDK not installed locally (CI installs it); 4 eval contract stubs that predate this work ("API backend implementation is pending"); 1 Redis Lua test needing `FLAME_TEST_REDIS_URL` |
| Registry | `python knowledge/ingestion/validate_registry.py` | 32 sources checked, 0 problems |
| Contract docs fresh | `python docs/tools/render_api_schemas.py --check` | exit 0 |
| Model artefact reproducible | `python -m ai.fire_safety.train_flex_outcome --check` | `artefact current` |
| Dataset checksums | `python knowledge/ingestion/install_datasets.py --verify-only` | 32 ok, 0 mismatched (others not installed: raw media is git-ignored) |
| Web lint / typecheck / build | `npm run lint` / `npm run typecheck` / `npm run build` | 0 errors, 0 warnings (5 pre-existing warnings cleared) / clean / 13 routes built |
| AURA Link 2 contract dry run | `AURA_BACKEND=<AURA d696fad>/aura_backend python tests/integration/aura_blueprint_dryrun.py` | 14 tools ACCEPTED (4 new fire-safety tools), 8 operations excluded |

New tests added by this work:

| Test file | What it checks |
|---|---|
| `apps/api/tests/test_fire_safety_api.py` | 9 tests: ranking against the lunar atmosphere, ranking that changes with the scenario, validation and 404s, NASA summary sections, insights that cite rows which resolve to `Test end` cells, inside vs outside the flight envelope, O₂ sweep monotonicity, **DB features = training features for all 261 FLEX tests**, artefact ↔ report ↔ table checksums |
| `apps/api/tests/test_ingestion.py` | committed tables present; ISA-Tab → citable document; en dash missing; `sccm` not a length; garbled-text detector; broken-font FLEX papers flagged |
| `apps/api/tests/test_ingestion_adapters.py` | NTRS count assertion updated to the real corpus: 24 reports, 284 pages |

Every response of the new operations is validated against its contract schema (`assert_contract_component`).

## 3. Model and retrieval evaluation (measured, not quoted)

| What | Result | Report |
|---|---|---|
| FLEX outcome model, 5× repeated CV grouped by test day | macro-F1 **0.540 ± 0.018** vs 0.271 majority baseline; extinction ROC-AUC **0.857 ± 0.010**; balanced accuracy 0.576 | [flex-outcome-model.md](docs/evaluation/reports/flex-outcome-model.md) |
| Same, held-out test days (viewed before the final selection rule; see disclosure) | macro-F1 0.640, extinction ROC-AUC 0.927 | same |
| numpy runtime vs scikit-learn | max probability difference 2.2 × 10⁻¹⁶ | same |
| Retrieval, live `/api/search`, 26 corpus-grounded questions | hybrid: hit@1 **0.81**, hit@5 **0.96**, MRR@10 **0.86**; lexical-only baseline: 0.31 / 0.31 / 0.31 | [retrieval-2026-11-07.md](docs/evaluation/reports/retrieval-2026-11-07.md) |
| Generated-answer quality (faithfulness, citation precision) | **Not run.** No language model was available | — |

## 4. End-to-end verification on the live stack

| Workflow | Result |
|---|---|
| Migrate → seed → ingest | 840 experiments (FLEX 274, BASS-II 129, SPICE 435 after 34 recorded duplicates, SAFFIRE-I 2); 24 PDFs, 284 pages, 280 chunks; 4 ISA-Tab documents, 35 sections; 44 pages OCRed (35 had a garbled text layer), 1 low-confidence; 0 quarantined. A second ingest is idempotent. |
| Vector index | 315 chunks embedded (`bge-small-en-v1.5-315-20261107`); after the OCR change only the 40 changed chunks were re-embedded |
| `/api/health` (auth on) | `healthy`; `llm: disabled` (honest); `api_version` 0.5.0; no token → 401 |
| Analyses through the API (write key) | `submit_demo_analyses.py`: BASS-II flight video (90 frames) and 2 SPICE ISS images → 3 × `completed` |
| Web proxy | new GETs 200; `/api/admin/*` 404 through the proxy |
| Browser journey | `node apps/web/scripts/demo-smoke.mjs`: **8/8 steps PASS**, 0 console errors, 0 failed API calls. Steps: dashboard, lunar scenario, investigation, evidence, explorer incl. refusal, chat, video, status |
| Mobile (iPhone 13 emulation) | dashboard renders; 0 px horizontal overflow |
| API image layout | Dockerfile `COPY` set reproduced in a temp dir; app imports and serves 4 key routes with 200 |

## 5. CI on GitHub (PR #24)

- Pushes before the final docs: all jobs green, including the AURA contract job.
- The final head is reported in the PR.

## 6. Defects found and fixed during this work

| Defect | Severity | Fix |
|---|---|---|
| A fresh clone had **0 experiments**: the PSI tables were git-ignored | Critical | Committed (CC0, ~130 KB) with checksums |
| API image would crash: `ai/fire_safety` not copied; PSI tables excluded from the build | Critical | Dockerfile + `.dockerignore` |
| 35 PDF pages indexed as gibberish (broken font maps) | High | Garbled-text detection → OCR; stale chunk/embedding cleanup |
| Deployed search lexical-only (index never built at start) | High | Index build at start in compose and Railway |
| En dash "not available" stored as text; SPICE `sccm` converted to metres | Medium | Ingest fixes + tests |
| `/api/health` reported API version 0.1.0 | Low | Single-sourced from the contract |
| UI: no navigation to 6 of 8 pages; dead buttons; hard-coded "14 Linked Docs"; History always opened the newest analysis; "Grounded" badge driven by `memory_used`; chat suggested a temperature question the system refuses | Medium | Fixed |

## 7. Independent code review (2026-11-07)

A separate reviewer agent read the new backend code. It found no crash-level defects. Findings and outcomes:

| Finding | Outcome |
|---|---|
| BASS-II coverage insight ignored the lower O₂ bound (a 10 % O₂ custom scenario was called "inside the range") | Fixed + test |
| A missing CO₂/He cell would be treated as "no diluent" | Fixed: treated as missing (no FLEX row is affected; the model artefact is unchanged) + test |
| The reduced-pressure insight cited pressure cells for outcome shares | Fixed: cites `Test end` cells and says the list is a sample + test |
| A test with a non-physical pressure counted as a pressure neighbour | Fixed + test |
| A corrupt metadata zip could abort the whole ingest | Fixed: quarantined + test |
| Re-ingest left evidence rows for pages that no longer yield text; a human review carried over to changed text | Fixed |
| The garbled-text heuristic could misfire on reference lists or non-English pages, and drops a page if OCR is unavailable | Kept, and listed under Unresolved: it flags no legitimate page in the current English corpus; Tesseract is installed in the image and CI |

## 8. Follow-up verification: ADR-006 to 009 (2026-11-12, PR #29)

Run on branch `anas/vibrant-sagan-fsnckf` after the four ADR builds, in the same kind of environment as §1 (Python 3.13, PostgreSQL 16.15 + pgvector holding the 2026-11-07 corpus, Redis 7, no Docker, no language model).

| Check | Command | Result |
|---|---|---|
| Full test suite | `python -m pytest` | **420 passed, 6 skipped, 0 failed** |
| Lint | `ruff check .` | All checks passed |
| Contract docs fresh | `python docs/tools/render_api_schemas.py --check` | exit 0 (contract 0.6.0) |
| Migrations on real data | `alembic upgrade head` on the 2026-11-07 database, then `downgrade 0007_chunk_search_tsv` and `upgrade head` again | `0007 → 0008 → 0009`, round trip clean |
| AURA Link 2 dry run | `AURA_BACKEND=<AURA d696fad>/aura_backend python tests/integration/aura_blueprint_dryrun.py` | **16 tools ACCEPTED**, 10 operations excluded, exit 0 |
| ADR-006 benchmark gate | `flame_retrieval_benchmark` against old `main`, the new stack, and the stack with the reranker, all on one database | Identical top 5 for all 26 questions; reranker hit@1 0.81 → 0.88 at about 0.5 s per search ([retrieval-2026-11-12.md](docs/evaluation/reports/retrieval-2026-11-12.md)) |
| Knowledge graph on PostgreSQL | `python -m flame_api.ingest` (graph built at the end) | 955 entities, 10,683 edges, consistency `ok` (4 spelling-variant candidates, non-blocking) |

New tests:
- `test_api_clients.py`: the admin scope;
- `test_video_checkpoints.py`: 8 tests, including a crash, recovery and resume giving a frame-for-frame identical result, and cancellation in every state;
- `tests/unit/test_search_stack.py` and `test_search_fusion.py`: the stack, the routed reranker and the rewrite;
- `test_answer_cache.py`: reranker cache keying;
- `test_knowledge_graph.py`: 11 tests over the real committed tables.

Not re-run: the web lint and build (no web code changed), the browser smoke test, Docker Compose, Railway, and generated-answer evaluation (still no language model here).

## Unresolved

- The garbled-text heuristic is tuned on this English corpus; a reference-list or non-English page could be mis-flagged in future documents (see §7).

- Docker Compose dry run and Railway redeploy: **not run** (no Docker daemon; no Railway access).
- Generated-answer evaluation: **not run** (no language model in this environment).
- Gold set and model labels: human review pending.

## Changelog
- 1.0.0 (2026-11-07): first version.
- 1.1.0 (2026-11-12): §8, verification of the ADR-006 to 009 builds.
