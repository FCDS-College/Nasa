# H-5: Offline acceptance tests

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas); automation with Ziad (E5) | Plan approved for Week 2; evidence partial | 1.0.0 | 2026-10-12 | 2H §8.8, §8.9 | `apps/api/tests/test_offline_routing.py`, `tests/unit/test_model_router.py`, `apps/api/tests/test_health.py` |

## 1. How disconnection is simulated

| Level | Method | Used for |
|---|---|---|
| A, unit | Fake providers, or `ai.providers.http.urlopen` replaced by a fake network. `socket.create_connection` is patched to fail the test on any real connection. | Every CI run |
| B, process | Real API + Postgres + Ollama on one host, with AURA configured at an unresolvable host (`https://aura.invalid`) and `offline_only` mode | 2026-10-11 run (§3) |
| C, network | The host loses its default route: `ip route del default`, or a network namespace with no route, or the cable physically unplugged | **Required by §8.8. Pending.** |

## 2. Scenarios

| # | Scenario (§8.8) | Expected | Automated test | Level B evidence | Level C |
|---|---|---|---|---|---|
| S1 | Internet disconnected before startup | Local services start; offline workflows available | `test_health.py::test_offline_only_reports_aura_as_blocked_and_never_probes_it` | API started in `offline_only` with AURA unreachable; `/api/ai/providers` lists aura `blocked` | Pending |
| S2 | Internet disappears during a cloud request | Safe failover to a compatible local model | `test_offline_routing.py::test_internet_drops_during_a_cloud_request_and_the_local_model_answers` | — | Pending |
| S3 | Cloud LLM unavailable | Local LLM handles language tasks | `test_model_router.py::test_cloud_preferred_uses_the_cloud_and_falls_back_to_local_when_it_fails` | ✅ answered by Ollama, AURA blocked (§3 run 1) | Pending |
| S4 | Cloud embedding service unavailable | Local embeddings support indexing and retrieval | `test_offline_routing.py::test_offline_embeddings_never_download_a_missing_model` | ✅ `vector_index build` embedded 37 chunks; `verify` ran with `HF_HUB_OFFLINE=1` | Pending |
| S5 | External research search unavailable | Uses local sources, discloses the limitation | n/a: Flame has no live external search (H-1 §2). Answers carry `knowledge_version`. Covered by `test_chat.py` (knowledge_version present). | ✅ answer carried `knowledge_version = bge-small-en-v1.5-37-20261011` | Pending |
| S6 | A video is already stored locally | Local video processing completes offline | Automated: `tests/unit/test_video_provider.py::test_video_task_routes_offline_and_returns_frames` (offline_only, real OpenCV, synthetic video) | `pytest tests/unit/test_video_provider.py` | Automated (provider level; API/job path pending) |
| S7 | Local LLM exceeds available memory | Controlled resource error, no crash | `test_offline_routing.py::test_a_local_model_out_of_memory_is_a_controlled_degraded_answer` | — | Pending |
| S8 | Local model missing or corrupt | Health reports it; actionable error | `test_offline_routing.py::test_a_missing_local_model_is_reported_by_health_with_an_actionable_reason`, `…_is_skipped_without_a_call` | ✅ with Ollama stopped: `llm` = down "No local language model is ready." (§3 run 3) | Pending |
| S9 | App restarts during a video job | Resumes or enters a recoverable state | Provider level: `test_resuming_the_same_work_dir_reuses_the_checkpoint` and `tests/cv/test_video_pipeline.py` (interrupted-run resume). A kill-and-restart run through the worker is not yet exercised | `pytest tests/unit/test_video_provider.py tests/cv/test_video_pipeline.py` | Partial |
| S10 | Connectivity returns | Eligible cloud operations resume | `test_model_router.py::test_the_circuit_opens_skips_the_dead_provider_then_half_opens_after_cooldown` | — | Pending |
| S11 | Offline-Only mode | No external AI requests | `test_offline_routing.py::test_offline_only_answers_locally_and_makes_no_external_request`; `test_model_router.py::test_offline_only_never_calls_an_external_provider`, `…_does_not_even_probe_external_providers` | ✅ zero `aura.invalid` lookups in the API log | Pending |
| S12 | Local answer with incomplete evidence | States uncertainty; no invented citations | `test_chat.py::test_an_answer_that_cites_nothing_is_flagged`; citations outside the retrieved set are dropped (`test_answer_is_written_by_aura_from_flame_evidence_only`) | ✅ run 1: the model said the passages did not answer the question | Pending |
| S13 | Local and cloud models disagree | Evidence preserved, model/version recorded | `test_offline_routing.py::test_local_and_cloud_answers_both_carry_their_provenance` | — | Pending |

## 3. Execution evidence

**Run 2026-10-11, Level B.**

| | |
|---|---|
| Commit | the working tree of `2afbc37` (same code) |
| Host | 4 vCPU, 15 GiB RAM, no GPU |
| Database | PostgreSQL 16 + pgvector (Ubuntu package postgresql-16-pgvector 0.6.0-1), migrations at `0004` |
| Corpus | 3 NTRS PDFs (39 pages, 37 chunks), index `bge-small-en-v1.5-37-20261011` |
| Model runtime | Ollama 0.5.7 serving `qwen2.5:3b-instruct-q4_K_M` |
| API environment | `FLAME_AI_EXECUTION_MODE=offline_only`, `FLAME_AURA_ENABLED=true`, `FLAME_AURA_BASE_URL=https://aura.invalid`, `FLAME_EMBEDDING_OFFLINE=true` |

| Run | Request | Result |
|---|---|---|
| 1 | `POST /api/chat` "How does oxygen concentration affect flame spread in microgravity?" | 200. `execution.provider = ollama`, `locality = local`, `mode = offline_only`, `fallback_used = false`, `latency_ms = 77774`. 6 sources cited, all from the retrieved set. The answer said the passages did not directly address the question (a cautious but wrong abstention: pages 5 and 10 of NASA/TM-2008-215260 discuss oxygen effects, and p. 10 was among the cited passages). |
| 2 | Two more questions (materials; extinction criterion) | 200. Ollama, 50,042 ms and 53,682 ms. The second answer only repeated the paper title (quality issue, H-7). |
| 3 | Ollama process stopped; `POST /api/chat` "flame spread oxygen" | 200. `warnings = [generation_unavailable]`, 6 sources returned, `execution.reasons = [{ollama: unavailable}, {aura: egress_blocked}]`. `/api/health`: `llm` = down, `aura` = disabled "AURA is blocked in offline_only mode." |
| — | API log | `grep -c aura.invalid` = 0 |

Overall status was `unhealthy` in run 3 only because MinIO, a required service, was not running in this container.

**CI (Level A).** 179 passed, 1 skipped at `2afbc37` (`python -m pytest` from the repo root, 2026-10-12).

## 4. Still required for the Definition of Done (§8.9 item 8)
1. One Level C run of S1–S13 on the Compose stack (H-6) by an engineer other than the Lead, recorded here with date, commit, mode, logs and pass/fail.
2. S6 and S9 are automated at provider level; add the API/worker path once an endpoint submits video jobs.

## Known limitations
- Level A fakes the HTTP layer. It proves the routing logic, not the runtimes' real failure modes.
- Level B is not Level C: DNS failure for `aura.invalid` is not the same as having no route.

## Changelog
- 1.0.0 (2026-10-12): plan, test mapping and the first Level B evidence.
