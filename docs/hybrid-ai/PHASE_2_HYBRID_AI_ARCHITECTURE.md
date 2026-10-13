# H-2: Hybrid AI architecture

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review (sign-off: Eman E1) | 1.0.0 | 2026-10-12 | 2H Tasks 2–3, M1, L-3 | `ai/providers/`, `ai/routing/`, `apps/api/flame_api/ai_runtime.py`, `generation.py` |

This document, together with [H-4](PHASE_2_HYBRID_AI_API_CONTRACTS.md), delivers L-3 (model routing and providers). Decisions: [ADR-003](../architecture/adr/ADR-003-provider-neutral-model-router.md) and [ADR-004](../architecture/adr/ADR-004-aura-boundary.md).

## 1. Target architecture mapped to real modules

```text
Next.js (apps/web) ──/api/*──▶ FastAPI (apps/api/flame_api/main.py, analysis.py)
                                   │  retrieval: Flame's own (main.search, vector_index)
                                   │  generation: flame_api/generation.py (prompts, schemas, validation)
                                   ▼
                     AI router (ai/routing/router.py) ◀── wiring: flame_api/ai_runtime.py
                     ├─ policies.py   modes, task→capability map, ordering, egress guard
                     ├─ health.py     circuit breaker + cached bounded probes
                     ├─ registry.py   providers + model_manifest.json (→ `model` table)
                     └─ tracing.py    optional OTel spans
              ┌─────────────────────┴───────────────────────┐
     External providers (ai/providers/cloud)       Local providers (ai/providers/local)
     aura.py      AURA /api/v3/chat                 ollama.py           Ollama /api/chat
     hf_space_cv.py  HF Space /api/analyze          vllm.py, llamacpp.py  OpenAI-compatible /v1
                                                    fastembed_embeddings.py  ONNX, CPU
                                                    cross_encoder.py     sentence-transformers
                                                    flame_cv.py          cv/flame_cv.py (OpenCV)
                                   ▼
            Local data services: PostgreSQL + pgvector · Redis (RQ, events) · MinIO
```

The RQ worker (`worker.py`) uses the same router for `vision.analyze` and `analysis.interpret`. Graph RAG (D4) and the video provider (Workstream A) plug in as new tasks and providers; the router doesn't change.

## 2. Execution modes

| Mode | Order of candidates | External providers | Use |
|---|---|---|---|
| `cloud_preferred` | external first, then local | allowed | Connected demos where AURA's model is preferred |
| `local_first` (default) | local first, then external | allowed as fallback | Normal operation; fewer external dependencies |
| `offline_only` | local only | **blocked**: never called, never probed, reported as `blocked` | Disconnected operation |

Setting the mode:
- **Env default:** `FLAME_AI_EXECUTION_MODE`.
- **Runtime:** `PUT /api/admin/ai/mode` (write token). This writes an `audit_event` row (`action = ai.mode.changed`, before/after, request ID) and switches the calling process immediately. Every other process (API replicas, the RQ worker) reads the newest such row at most every 10 s (`ai_runtime.current_mode_override`), so all of them converge without restarts. If the database is unreachable, a process keeps the mode it already has.

## 3. Local vs external classification

Locality is network location, not hardware.

| Provider | Locality | Capabilities | Modalities |
|---|---|---|---|
| `ollama` | local | chat, structured | text |
| `vllm` (L40S on the same network) | local | chat, structured | text |
| `llamacpp` | local | chat, structured | text |
| `fastembed` | local | embeddings | text |
| `cross_encoder` | local | reranking | text |
| `flame_cv` | local | vision | image |
| `aura` | external | chat, structured | text |
| `hf_space` | external | vision | image |

## 4. Routing inputs and policies

Mapping of §8.5 Task 3 inputs:

| Input | How it is used |
|---|---|
| 1–2. task, required capabilities | `TASKS` in `policies.py`: `chat.answer`, `analysis.interpret` → structured; `text.generate` → chat; `embed.query`, `embed.documents` → embeddings; `rerank`; `vision.analyze` → vision + image; `video.analyze`; `speech.transcribe` |
| 3. network and provider health | Cached probe state (`HealthMonitor`, TTL 15 s, probe timeout ≤ 2 s, run in parallel by `/api/health` and `/api/ai/providers`, never on the request path) and the circuit breaker |
| 4. local model availability | Probes check the model itself: Ollama `/api/tags`, OpenAI-compatible `/v1/models`, the fastembed cache directory. A missing model reports `model_missing`. |
| 5. GPU/RAM availability | Not probed. A runtime's own out-of-memory error maps to `resource_exhausted`, and the router moves on. |
| 6. task complexity | Not used yet. P2 "adaptive model selection". |
| 7. latency requirements | Per-provider timeouts: `FLAME_LLM_TIMEOUT_S` (default 180 s, sized for about 5–10 tokens/s CPU at 500 tokens), `FLAME_AURA_TIMEOUT_S`, `FLAME_CV_TIMEOUT_S` |
| 8. context window | Recorded in `ProviderInfo.context_window` and the manifest; requests stay within it by construction (≤16 passages × ≤2000 chars) |
| 9. internet-only information | `Task.needs_internet` (none today; Flame does no live web search) |
| 10. permitted in offline_only | `policies.permitted()` |

**Policies (all tested in `tests/unit/test_model_router.py`):**
- **Ordering:** locality preference for the mode, then registration priority (vLLM 10 < Ollama 20 < llama.cpp 30 < AURA 50), then name. The order is deterministic.
- **Circuit breaker:** opens after `FLAME_PROVIDER_FAILURE_THRESHOLD` (3) consecutive failures and stays open for `FLAME_PROVIDER_COOLDOWN_S` (30 s). It then half-opens for one trial call; a failed trial restarts the cooldown. A `invalid_request` error is our own fault and never trips it.
- **Fallback:** only for fallback-eligible codes (`unavailable`, `timeout`, `model_missing`, `resource_exhausted`, `invalid_output`, `not_configured`, `egress_blocked`, `unsupported`).
- **Idempotency:** a non-idempotent call whose request may have reached the provider (`request_sent = true`) is not sent anywhere else. Generation calls are idempotent by construction: same input, idempotency key = request or analysis ID, temperature 0.
- **Loop prevention:** each provider is tried at most once per request.
- **No modality downgrade:** a task needs the capability *and* the modality. A text-only model never receives `vision.analyze`, even if it claims vision.
- **Validation inside the route:** Flame's own output validation (`generation.py`) runs in the routed call. A provider that answers with unusable output counts as `invalid_output`, and the next one is tried.
- **Observability:** each decision is logged (`routing_decision` / `routing_attempt_failed` / `routing_exhausted`), counted (`/api/ai/providers` → `decisions`) and, when enabled, traced (`router.route`, `provider.<name>` spans).

## 5. Fallback registry (per task)

| Task | local_first order (default config) | When nothing is left |
|---|---|---|
| `chat.answer` | vllm → ollama → llamacpp → aura | `200` with evidence only, `warnings: [generation_unavailable]`, `execution.reasons` |
| `analysis.interpret` | same | interpretation `unavailable`; CV result unaffected |
| `embed.query` / `embed.documents` | fastembed | search drops to lexical (`retrieval.mode = lexical`); index build fails loudly |
| `vision.analyze` | preferred CV provider (`FLAME_CV_PROVIDER`) → the other | analysis `failed` with `MODEL_UNAVAILABLE` (retryable) |
| `rerank` | cross_encoder (if enabled) | ranking unchanged (Eman's pipeline decides) |

## 6. Dependency boundaries

| Layer | May import | Must not import |
|---|---|---|
| `ai/providers/contracts` | stdlib | anything else in the repo |
| `ai/providers/{local,cloud}` | contracts, `ai/providers/http.py`, `cv` (flame_cv only); vendor SDKs lazily inside functions | `apps/api`, `flame_api` |
| `ai/routing` | contracts | adapters, `flame_api` |
| `flame_api.*` (except `ai_runtime`) | `ai.routing`, contracts | concrete adapters, except the compatibility shims `aura_integration.py` and `hf_cv.py` |
| `flame_api/ai_runtime.py` | everything above | — |

## 7. The offline-only egress guarantee

1. `policies.permitted()` returns `False` for every `EXTERNAL` provider in `offline_only`.
2. `Router._route` checks permission **before** the circuit, the health state or the call. A blocked provider yields only the reason `egress_blocked`.
3. `Router.refresh_health` skips blocked providers, so not even a readiness probe leaves.
4. Embeddings with `FLAME_EMBEDDING_OFFLINE=true` set `HF_HUB_OFFLINE=1` and refuse to download.
5. Tests:
   - `apps/api/tests/test_offline_routing.py` replaces `socket.create_connection` with a function that fails the test, and asserts that the AURA host never appears in the request log;
   - `test_health.py::test_offline_only_reports_aura_as_blocked_and_never_probes_it` makes the AURA probe raise.

**What the guarantee does not cover:**
- processes outside the router: `knowledge/ingestion/*` download scripts, `pip` and `npm`, and the Ollama runtime's own update checks (Ollama has none by default);
- the web app's browser.

H-6 tells operators to run offline hosts on a network without a default route. That is the backstop.

## Known limitations
- The circuit breaker and the health cache are per process; they are not shared.
- GPU/RAM headroom is not probed (input 5). An out-of-memory error is handled after the fact.
- No automatic selection among several local models (P2).
- The mode override is read from the database. Without a database, a process keeps its current mode.

## Changelog
- 1.0.0 (2026-10-12): describes the router as built in PR #14.
