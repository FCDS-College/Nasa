# AURA × Flame integration audit (2026-10-30)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas), audit run by Claude Code | Current; supersedes [AURA_INTEGRATION_STATUS.md](AURA_INTEGRATION_STATUS.md) §0 for the facts below | 1.0.0 | 2026-10-30 | L-12, ADR-004 | `ai/providers/cloud/aura.py`, `ai/providers/http.py`, `docs/api/openapi.json`, `tests/integration/aura_blueprint_dryrun.py`; AURA `aura_backend/aura_core/api/v3.py`, `aura_core/adapters/connectors/openapi.py` |

Both repositories were inspected: Flame at `7340782` plus this audit's changes, and AURA `anasibrahimgnedy-collab/AURA-AI` at HEAD `6417c43` (read-only). Endpoint-level detail for AURA engineers is in [API_INTEGRATION_REFERENCE.md](API_INTEGRATION_REFERENCE.md).

## 1. Integration architecture (as implemented)

```
                 Link 2 (AURA → Flame): read-only tools compiled from Flame's OpenAPI
 AURA agent ──── GET /api/{health,dashboard/counts,search,documents,experiments,evidence,analyses} ───▶ Flame API
 orchestrator        Authorization: Bearer <Flame read token> (AURA connector secret, https only)

                 Link 1 (Flame → AURA): optional external LLM provider behind Flame's router
 Flame API/worker ── POST /api/v3/chat (svc-flame service key; tools/memory/knowledge off;
                     evidence in `context`; response_schema; Idempotency-Key) ─────────────────▶ AURA

 AURA Flutter client: no Flame references at all. It reaches Flame's science only through the AURA backend.
```

Verified against the intended boundary (*AURA → Flame API → scientific platform*):
- **Yes.** AURA reaches Flame only through the versioned OpenAPI contract, with GET operations only (`adaptation/factories/tools.py:353` compiles GETs only).
- **No direct coupling.** The Flutter client has no Flame code or config: a grep for flame, freefall, nasa, `FLAME_` and openapi over Dart and config files finds nothing. AURA never touches Flame's database, vector index, storage or models.
- **Loop prevention.** `/api/chat`, `/api/ai/providers` and `/api/admin/ai/mode` carry `x-aura-exclude: true`. AURA honours it (`openapi.py:75,300-313`), and the dry run reports "excluded by x-aura-exclude: 3 operations, 3 reported by discovery".
- **Firebase.** Not involved in either link. AURA service keys bypass the JWT path (`aura_service.py:59-62`). Link 2 uses a vaulted static bearer token. Firebase identities are not mapped to Flame.

## 2. Status by capability

| Capability AURA needs | Flame operation | AURA tool | Status |
|---|---|---|---|
| System health and readiness | `GET /api/health` | `api_get_health` | Implemented, tested, runtime-verified |
| Dashboard counts | `GET /api/dashboard/counts` | `api_get_dashboard_counts` | Implemented, tested, runtime-verified (persisted rows) |
| Search documents and experiments, with sources | `GET /api/search` | `api_search` | Implemented, tested, runtime-verified (hybrid, evidence IDs, page locators) |
| Document / experiment detail | `GET /api/documents[/{id}]`, `GET /api/experiments[/{id}]` | 4 tools | Implemented, tested; experiments not runtime-verified (no data here) |
| Evidence and citations | `GET /api/evidence/{id}` | `api_get_evidence` | Implemented, tested, runtime-verified |
| Analysis status and results (image **and video**) | `GET /api/analyses[/{id}]` | `api_list_analyses`, `api_get_analysis` | Implemented, tested, runtime-verified. Video results are new in contract 0.3.0. |
| Structured scientific answer (AURA asks Flame) | `POST /api/chat` | **excluded by design** | AURA's own LLM composes answers from `api_search` + `api_get_evidence`. Exposing Flame's chat would create the Flame → AURA → Flame loop (ADR-004). |
| Start an image or video analysis | `POST /api/analyses` | not compiled (AURA compiles GET only) | Implemented. Deliberately not reachable by AURA today: it is a write, and needs the write token. |
| Artifacts (images, video bytes) | `GET /api/analyses/{id}/artifacts/{kind}` | not compiled (binary response) | Implemented. AURA can link to it; it cannot use it as a JSON tool. |
| Research history | `GET /api/analyses` (analysis history) | `api_list_analyses` | Analyses only. **Search and chat history are not persisted** (MISSING; P3, needs product need). |
| Model and service availability | `GET /api/health` → `ai` block | `api_get_health` | Implemented (the `ai` block lists providers, health and mode). `/api/ai/providers` stays excluded. |
| Async research operations | analyses: 202 + `Location` + `poll_after_ms` | — | Implemented for analyses. Search and chat are synchronous. |

## 3. Defects found and their status

| # | Side | Defect | Impact | Status |
|---|---|---|---|---|
| I1 | Flame (Link 1) | AURA answers **422 `output_invalid`** when its model fails the `response_schema`. Flame mapped every 422 to `INVALID_REQUEST`, which the router never falls back from (`ai/providers/http.py`). | A schema miss by AURA's model stopped routing instead of falling back to the local model | **Fixed**: `output_invalid` → `INVALID_OUTPUT` (fallback-eligible). FastAPI 422s stay `INVALID_REQUEST`. Test: `test_aura_schema_failure_is_fallback_eligible`. |
| I2 | Flame and AURA (Link 1) | AURA stores and **replays any <500 response for 24 h** per Idempotency-Key, including turn failures returned as 400/422/429, and returns 422 `idempotency_key_reused` for the same key with a different body (`api/idempotency.py:145-151`). Flame used the bare `analysis_id`/`request_id` as the key. | Re-interpreting an analysis with new evidence failed for 24 h; a cached 429 was replayed | **Fixed on Flame's side**: key = `<id>:<sha256(body)[:16]>`. Exact retries are still deduplicated; a changed body is a new request. Test: `test_idempotency_key_changes_with_the_body_and_context_is_capped`. **AURA-side change still recommended** (§5, A1). |
| I3 | Flame (Link 1) | AURA rejects `context[].text` over 2000 chars with 422 (`ContextEntry`). Flame did not cap it in the provider. | Possible hard failure, no fallback | **Fixed**: the provider caps text at 2000 (`MAX_CONTEXT_TEXT`). The worker's measurement summary was already ≤ 2000 (existing test). |
| I4 | Both | Three AURA error body shapes (`{error,…}`, `{"detail":{…}}`, FastAPI `{"detail":[…]}`) | Flame branches on status code, so nothing breaks; logging only parses one shape | Open. AURA A2. |
| I5 | AURA | `/health/ready` is 200 when **any** provider is healthy, but Flame sends `require_local: true` by default. If no AURA provider is marked local, every call is a 503 `all_providers_failed` while health says "up". | Flame's health shows AURA "up", but every call falls back | Open. Mitigated: Flame falls back on 503. AURA A3, or set `FLAME_AURA_REQUIRE_LOCAL=false` where AURA's model is remote by design. |
| I6 | AURA docs | `docs/guides/flame-integration-runbook.md:47` says "all 8 tools"; there are 10. Line 38 suggests serving Flame's read API anonymously; Flame requires a bearer token, and AURA sends credentials only over https. | Misconfiguration risk | Open. AURA A4. |
| I7 | Flame | `meta.api_version` said 0.1.0 while the contract was 0.2.0 | AURA could not tell which contract it was talking to | **Fixed**: 0.3.0, pinned to `info.version` by a test |
| I8 | Flame | 405 returned `INTERNAL_ERROR` | Misleading error for a client bug | **Fixed**: `METHOD_NOT_ALLOWED` |

## 4. Contract compatibility (Link 1 field check)

Verified by reading `v3.py:202-247,430-618` against `aura.py`:
- **Request.** Every field Flame sends is accepted (`message`, `agent`, `plan`, `use_*`, `require_local`, `max_output_tokens` 400/500 within 16–8192, `temperature`, `context` ≤ 16 entries, `response_schema` ≤ 8000 chars).
- **Context IDs and sources.** Flame's ULID evidence IDs and its sources (`flame/image_measurement`, `flame/source_evidence`, sanitized titles) match AURA's patterns.
- **Response.** `message`, `data`, `model`, `provider`, `cached` and `usage` cover everything Flame reads.
- **Timestamps.** No timestamps cross Link 1. Link 2 timestamps are RFC 3339 UTC with `Z` (`_timestamp`/`_utc`). One exception: `GET /api/documents/{id}` formats `ingested_at` without normalizing a naive datetime (`main.py:816`). Postgres returns aware values, so it is correct on the supported database.
- **Timeouts.** AURA's per-call LLM timeout is 60 s; Flame waits up to `FLAME_AURA_TIMEOUT_S` (120 s). Compatible.

## 5. Required AURA-side changes (not made here; AURA was inspected read-only)

| ID | Change | Why |
|---|---|---|
| A1 | Do not store retryable outcomes (409/429/503) or `output_invalid` in the idempotency cache | Prevents replaying transient failures for 24 h (I2). Flame's body-hash key already avoids the `idempotency_key_reused` case. |
| A2 | One error envelope for dependency-raised errors (auth, rate limit) | Consistent client handling (I4) |
| A3 | Readiness that reflects `require_local`: e.g. `providers.local_healthy` in `/health/ready` | Health should predict whether Flame's call can succeed (I5) |
| A4 | Fix the runbook: 10 tools; Flame requires a bearer read token | I6 |
| A5 | Bump the pinned revision in Flame's `aura-link2-contract.yml` from `c10fd13` once A1–A4 land, and re-run the dry run | The pin predates PR #166+; HEAD `6417c43` passes the dry run against contract 0.3.0 |

## 6. Integration test results

| Test | How | Result |
|---|---|---|
| Link 2 compile against AURA HEAD | `AURA_BACKEND=…/aura_backend python tests/integration/aura_blueprint_dryrun.py`, before and after contract 0.3.0 | 10 tools ACCEPTED, 3 excluded, exit 0 (both runs) |
| AURA's own tests for service keys, discovery, compiler, structured output, connectors, caller context and HTTP idempotency | AURA venv from `requirements.lock` | 251 passed, 2 skipped |
| Flame Link 1 tests | `apps/api/tests/test_aura_integration.py` | all pass, including 2 new tests (I1, I2/I3) |
| AURA → Flame HTTP calls with auth | The exact GETs AURA's tools make, with the read token, against the live stack; no token → 401; read token on a write → 401 | pass |
| Real AURA → Flame over the network | Needs a deployed AURA with a Flame connector and secret | **Not run** (no AURA deployment or credentials here) |
| Real Flame → AURA `/api/v3/chat` | Needs an AURA service key | **Not run**. Covered by mocked-HTTP tests only. |
| Reliability: invalid auth, bad payloads, provider down, slow model, recovery, duplicate submission | Flame live stack + tests | 401s, 400/415/422 validation, idempotent analysis creation, outage → evidence-only, recovery ~30 s; all pass |
