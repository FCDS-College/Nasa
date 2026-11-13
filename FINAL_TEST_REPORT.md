# Final test report: Flame in Freefall

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas), run by Claude Code | Current | 1.5.0 | 2026-11-13 | T7, ADR-006–009, ADR-013 | whole repository |

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
| ADR-006 benchmark gate | `flame_retrieval_benchmark` against old `main`, the new stack, and the stack with the reranker, all on one database | Identical top 5 for all 26 questions; reranker (sentence-transformers) hit@1 0.81 → 0.88 at about 0.5 s per search. Superseded by §9's fastembed run ([retrieval-2026-11-12.md](docs/evaluation/reports/retrieval-2026-11-12.md)) |
| Knowledge graph on PostgreSQL | `python -m flame_api.ingest` (graph built at the end) | 955 entities, 10,683 edges, consistency `ok` (4 spelling-variant candidates, non-blocking; resolved by reviewed aliases in PR #30: 951 entities, 0 candidates) |

New tests:
- `test_api_clients.py`: the admin scope;
- `test_video_checkpoints.py`: 8 tests, including a crash, recovery and resume giving a frame-for-frame identical result, and cancellation in every state;
- `tests/unit/test_search_stack.py` and `test_search_fusion.py`: the stack, the routed reranker and the rewrite;
- `test_answer_cache.py`: reranker cache keying;
- `test_knowledge_graph.py`: 11 tests over the real committed tables.

Not re-run locally: the web lint and build (no web code changed; CI ran them green), the browser smoke test, Docker Compose, Railway, and generated-answer evaluation (still no language model here).

**CI on GitHub (PR #29).** All five jobs green on the merged head `f6ca06f`: Python lint and tests, web lint/typecheck/build, migrations with seed and ingest on PostgreSQL + pgvector, secret scan, and the AURA Link 2 contract. The contract job first failed at checking out AURA, because the `AURA_REPO_TOKEN` secret no longer worked. It passed once the owner replaced the token.

## 9. Follow-up verification: reranker default and graph aliases (2026-11-12, PR #30)

| Check | Command | Result |
|---|---|---|
| Full test suite | `python -m pytest` | **423 passed, 6 skipped, 0 failed** |
| Unit tree with an empty model cache (as on CI) | `HF_HOME=<empty dir> python -m pytest tests/unit` | 113 passed |
| fastembed vs sentence-transformers cross-encoder | the same 4 (query, passage) pairs through both | identical scores (−3.625, −11.351, −11.034, 0.259) |
| Retrieval with the default reranker | `flame_retrieval_benchmark`, one database, fused vs reranked | hit@1 0.81 → **0.88**, MRR@10 0.86 → **0.91**, recall@5 0.83 → **0.88**, hit@5 0.96 unchanged; about 0.7 s per search ([report](docs/evaluation/reports/retrieval-2026-11-12.md), follow-up section) |
| Offline model preparation | `python -m ai.providers.local.cross_encoder prepare --cache-dir <dir>`, then `verify` | downloaded in about 5 s; offline load OK (exit 0) |
| Knowledge graph with the reviewed aliases (PostgreSQL) | `python -m flame_api.knowledge_graph build`, then `check` | 21 edges re-pointed, 4 variant entities dropped; **951 entities**, 10,683 edges; all five checks 0 |
| AURA runbook (AURA-AI #232) | dry run of Flame `main` `80b9c21` against AURA `ad215d3` and `d696fad` | 16 ACCEPTED, 10 excluded, exit 0, both |
| CI (PR #30) | — | all five jobs green on the merged head `0aec4f7` |

New tests:
- `tests/unit/test_cross_encoder_provider.py`: offline means `model_missing` and never a download; scores come back best first; long passages are truncated;
- `test_knowledge_graph.py`, now 12 tests: a reviewed variant resolves to its canonical entity and keeps its own cell.

Defects CI found in PR #30's own tests, both fixed before merge:
- The provider test assumed fastembed was installed. CI's repo-root job does not install it.
- The offline test left `HF_HUB_OFFLINE=1` set for the rest of the session, so the existing `test_embeddings` could not download its model on CI. It passed locally only because the model was cached. This was reproduced with an empty `HF_HOME` and fixed with `monkeypatch.setenv`.

Not run: the browser smoke test against the reranked search, Docker Compose, Railway, and generated-answer evaluation.

**AURA-AI #232's own CI did not run.** Its Repo Hygiene jobs were never assigned a runner (`runner_id: 0`, about 2 s, no log), including on a re-run. The same checks run locally on the branch passed:
- the tracked-artefact check;
- the 27 hygiene tests;
- actionlint 1.7.12.

## 10. Knowledge Graph page (2026-11-12, PR #32)

| Check | Command | Result |
|---|---|---|
| Web typecheck, lint, build | `npm run typecheck`, `npm run lint`, `npm run build` | clean; 0 warnings; `/knowledge` built |
| Proxy | `GET /api/graph/entities?type=investigation` through the web app; `GET /api/admin/graph/consistency` through it; the API without a key | 4 investigations (BASS-II, FLEX, SAFFIRE-I, SPICE); 404 (not forwarded); 401 |
| Browser journey, API with auth on, PostgreSQL graph, reranker on | `node apps/web/scripts/demo-smoke.mjs` (9 steps; new step 08 opens FLEX, then walks Extinction 2 hops over "ended in" and "burned") | **9/9 PASS**. Not clean: no S3 stand-in ran, so `/api/health` answered 503 seven times and one image overlay artifact once (`object_storage_health=down`); none involves `/knowledge` |
| Phone (iPhone 13 emulation) | Playwright | 0 px horizontal overflow; after a tap the details scroll into view (top at 181 px, was 631 px before the fix) |
| CI (PR #32) | — | all four jobs green on the merged head `8277c85` (Python lint and tests, web lint/typecheck/build, migrations with seed and ingest on PostgreSQL + pgvector, secret scan); merged to `main` as `3ce2d69`. The AURA Link 2 contract job did not run: it runs only when `apps/api/`, the contract or the dry run changes, and PR #32 changed none of them |

## 11. AURA integration re-checked against AURA `main` (2026-11-12)

AURA `main` was at `667c7c4`, 218 commits after the pinned `d696fad`. Between the two revisions these are byte-for-byte unchanged:
- AURA's OpenAPI connector and adaptation pipeline;
- service keys and caller context;
- idempotency;
- the `/api/v3/chat` request model, apart from one optional desktop field.

| Check | Command | Result |
|---|---|---|
| Link 2 dry run, CI's own setup | Python 3.12 venv with only `PyYAML==6.0.3`; `AURA_BACKEND=<AURA 667c7c4>/aura_backend python tests/integration/aura_blueprint_dryrun.py` | **16 ACCEPTED**, 10 excluded, no `not reachable` lines, exit 0. The CI pin moved to `667c7c4` |
| AURA's Flame-facing tests, AURA's locked environment | Python 3.11 venv from `requirements.lock` + `requirements-dev.lock` (hashes checked; no drift warning); 11 files: caller context, image turns, adaptation compiler/connectors/discovery, HTTP idempotency, service keys, structured output, data classification, kernel degradation, provider wire contracts | **389 passed** |
| AURA's context guards on Flame's evidence | AURA's `default_context_guards()` from `d696fad` and from `667c7c4`, chained as AURA's pipeline does, over every `evidence.excerpt` in Flame's database (first 2000 characters, as Flame sends) | Both revisions: **10,562 passed, 0 dropped**. 67 PDF passages Unicode-normalised (`encoding` redact: NFKC), none quarantined |
| Flame changes | `pytest apps/api/tests/test_aura_integration.py`, `test_health.py`; then the full suite | 6 new tests (AURA error slug kept and logged, a non-identifier slug not echoed, `local_healthy` with and without `require_local`, an older AURA without the field) and 1 health test; full suite **429 passed, 6 skipped**; `ruff` clean; contract docs current |
| AURA's live targets | `GET /health/ready` on `aureon-ai.tech` and `aura-ai-production-03a4.up.railway.app`, 15:54 UTC | Both **404 "Application not found"** from Railway's edge. No live AURA to run either link against |

What changed in AURA that matters to Flame:
- **A new error.** AURA added 503 `capability_unavailable` (`retryable: false`) for a turn that no permitted model could answer. Flame already mapped it to `unavailable` and fell back. It now also keeps the slug in the error and logs it as `upstream=…`.
- **A gap that was always there.** AURA classifies caller `context` as SENSITIVE, which was already true at `d696fad`. A hosted-only AURA therefore cannot answer Flame unless its operator raises a slot's data ceiling and Flame stops requiring local. Neither Flame's nor AURA's docs said so; [docs/integration/README.md](docs/integration/README.md) §5 now does.

## Unresolved

- The garbled-text heuristic is tuned on this English corpus; a reference-list or non-English page could be mis-flagged in future documents (see §7).

- Docker Compose dry run and Railway redeploy: **not run** (no Docker daemon; no Railway access).
- Generated-answer evaluation: **not run** (no language model in this environment).
- Gold set and model labels: human review pending.
- AURA's GitHub Actions were not assigning runners on 2026-11-12 (account-level); AURA-AI #232 merged on locally run checks.
- No AURA deployment was reachable on 2026-11-12 (§11), so neither link was run live.

## 12. Apollo 1 historical scenario, coverage verdict and gravity (2026-11-13, ADR-013, contract 0.7.0)

Run on branch `ccr-93d3f1f0-bf65vh`: Python 3.13, PostgreSQL 16 + pgvector (apt), Redis 7, `moto_server` as S3, Tesseract installed, no Docker, no language model.

| Check | Command | Result |
|---|---|---|
| Full test suite | `python -m pytest` | **661 passed, 31 skipped, 1 xfailed, 0 failed** |
| Lint | `ruff check .` | All checks passed |
| Web | `npm run lint && npm run typecheck && npm run build` | all exit 0 |
| Contract docs fresh | `python docs/tools/render_api_schemas.py --check` | exit 0 (contract 0.7.0) |
| Registry | `python knowledge/ingestion/validate_registry.py` | 35 sources checked, 0 problems |
| Checksums | `python knowledge/ingestion/install_datasets.py --verify-only` | 35 ok, 0 mismatched |
| New NTRS reports | `python knowledge/ingestion/fetch_ntrs.py --dry-run`, then without the flag | 3 accepted (8.4 MB), all public-use, registered |
| Ingest on PostgreSQL | `python -m flame_api.ingest`, then `vector_index build` | 840 experiments, 27 PDF documents, 486 pages, 480 chunks, 48 OCR pages, 0 quarantined; 515 chunks embedded |
| Browser journey | `npm run smoke -- http://127.0.0.1:3000 <dir>` | **11/11 PASS**, `Demo journey passed.` (02b Apollo 1 refusal, 02c Orion alternative) |
| FLEX model unchanged | `python -m ai.fire_safety.train_flex_outcome --check` | `artefact current`, exit 0 |
| AURA Link 2 dry run at 0.7.0 | `tests/integration/aura_blueprint_dryrun.py` | **not run here** (no AURA checkout); CI job `aura-link2-contract` runs it on the PR |

New tests:
- `tests/unit/test_historical_scenarios.py` (8): the schema; every cited page exists in a registered, committed report, and each quote appears verbatim on its page; loader rejection; custom gravity; the verdict (`none` with the nearest test and the gap, gravity alone, `partial`).
- `apps/api/tests/test_fire_safety_api.py` (+6): Apollo 1 verdict `none` over all 840 tests with cited nearest-test cells; the model refuses it with O₂ and gravity reasons; Earth-gravity air is refused; Orion is the alternative and is covered and estimated; the history endpoint is page-cited and returns 404 for mission scenarios; the sweep reaches 100 % O₂ while the in-range grid is unchanged; mission verdicts.
- `apps/api/tests/test_ingestion_adapters.py`: NTRS count 24 → 27, pages 284 → 486.

Found and fixed during the browser run: the Knowledge Graph page threw `Cannot read properties of undefined (reading 'toLowerCase')`. PR #43's NLP graph returns `platform` and `instrument` entities (contract-listed since 0.6.0), and the web client's type list lacked them. The cause predates this branch, and none of the affected edges come from the new reports.

## Changelog
- 1.0.0 (2026-11-07): first version.
- 1.1.0 (2026-11-12): §8, verification of the ADR-006 to 009 builds.
- 1.2.0 (2026-11-12): §8 CI results; §9, verification of PR #30 and AURA-AI #232.
- 1.3.0 (2026-11-12): §10, the Knowledge Graph page.
- 1.3.1 (2026-11-12): §10 CI results on PR #32's merged head.
- 1.4.0 (2026-11-12): §11, the AURA integration re-checked against AURA `main` `667c7c4`.
- 1.5.0 (2026-11-13): §12, the Apollo 1 scenario, coverage verdict and gravity (ADR-013, contract 0.7.0).
