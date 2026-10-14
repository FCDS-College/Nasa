# API changelog

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | — | 2026-10-12 | L-4, M6 | `docs/api/openapi.json`, `apps/api/flame_api/` |

Semver applies to `docs/api/openapi.json` `info.version`. Breaking changes need a minor bump while we are pre-1.0, an entry here, and one release of deprecation where practical.

## 0.2.0 (2026-10-12, PR #14)

**Added**
- `GET /api/documents`: list with `source_id[]`, `document_type`, `q` (title), `page`, `page_size` ≤ 100 (M6).
- `GET /api/experiments`: list with `source_id[]`, `gravity_regime`, `fuel_or_material`, `investigation`, pagination; each item has `condition_count` (M6).
- `POST /api/chat` is now in the contract (`ChatRequest` / `ChatResponse`), marked `x-aura-exclude: true` (ADR-004).
- `GET /api/ai/providers` (`AiProvidersResponse`): execution mode, providers, health, circuit, decision counters. `x-aura-exclude`.
- `PUT /api/admin/ai/mode` (`ModeChangeRequest` → `ModeChangeResponse`): write token, audited. `x-aura-exclude`.
- `HealthResponse.ai` (optional): `{mode, providers}`.
- `ChatResponse.execution`: `ExecutionMetadata` when a model answered, `RoutingFailure` when none could, `null` when no evidence matched.
- `Interpretation.execution`, `PipelineInfo.execution` (optional).
- `StatementOrigin` gains `model_interpretation`.
- `ErrorCode` gains `AUTHENTICATION_REQUIRED` (the middleware already returned it; contract drift fixed) and `CHAT_UNAVAILABLE`.
- Tag `Admin`.

**Changed**
- `Interpretation.provider` is now any provider name (string ≤ 64, nullable). It was the enum `["aura", null]`. Clients that switched on `"aura"` keep working; new values are `ollama`, `vllm`, `llamacpp`.
- `services.llm` in `/api/health` reflects the router's local language models. Before, it was always `disabled`.
- Chat when no model can answer: **was** `502 AURA_UNAVAILABLE`; **now** `200` with the retrieved `sources`, a fixed explanatory `answer`, and warning `generation_unavailable`. This is a behaviour change for clients that treated 502 as "show retry". The web chat already renders `warnings`.
- `CHAT_UNAVAILABLE` (503) now means "no language model configured or permitted in the current mode", not "AURA disabled".

**Deprecated**
- `AURA_UNAVAILABLE`: no longer emitted by chat. Kept in the enum for one release; to be removed in 0.3.0.

**Fixed**
- `API_SCHEMAS.md` was stale relative to `openapi.json` on `main`; it is regenerated and CI-checked now.

## 0.1.0 (MVP, `e73dcf1`)
The ten MVP operations: health, dashboard counts, search, document, experiment, evidence, analysis create/list/get/artifact.

## Known limitations

- `API_SCHEMAS.md` is generated from `openapi.json` (`python docs/tools/render_api_schemas.py`), so do not hand-edit it. CI runs `--check`.
- Pre-1.0: breaking changes only bump the minor version.
