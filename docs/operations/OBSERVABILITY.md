# L-9: Observability guide

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review (sign-off: Ziad E5) | 1.0.0 | 2026-10-12 | M12, §11 | `apps/api/flame_api/telemetry.py`, `ai/routing/tracing.py`, `main.py` middleware |

## 1. Enabling tracing

```bash
pip install -e "apps/api[observability]"
FLAME_OTEL_ENABLED=true OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318 uvicorn flame_api.main:app
```

Without `OTEL_EXPORTER_OTLP_ENDPOINT`, spans go to the console. Without the extra, or with `FLAME_OTEL_ENABLED=false` (the default), every span is a no-op and the router has no OpenTelemetry dependency at all.

## 2. Spans and attributes

| Span | Where | Attributes |
|---|---|---|
| `http.request` | API middleware | `http.method`, `http.route`, `http.status_code`, `flame.request_id` |
| `chat.retrieve` | `/api/chat` retrieval | `flame.request_id`, `flame.passages` |
| `chat.generate` | `/api/chat` generation | `flame.request_id`, `flame.knowledge_version` |
| `retrieval.vector` | `vector_index.search_chunks` | `flame.limit` |
| `router.route` | every routed call (API and worker) | `flame.task`, `flame.mode`, `flame.provider`, `flame.locality`, `flame.fallback_used` |
| `provider.<name>` | each provider attempt | `flame.provider`, `flame.locality`, `flame.model`, `flame.task` |

Verified by `apps/api/tests/test_telemetry.py` with the in-memory exporter. One request produces one trace containing `http.request → router.route → provider.ollama`.

Path coverage against the plan's "API → orchestration → cache → retrieval → rerank → provider/CV → persistence":
- API, retrieval, provider and CV (through `router.route` in the worker) are covered.
- Cache (M4) and rerank (M2) get spans when those land.
- Persistence: add `opentelemetry-instrumentation-sqlalchemy` if needed.

## 3. Structured log fields

Every request logs `request_id=… method=… path=… status=… duration_ms=…`. The routing and data events are:

| Event | Fields |
|---|---|
| `routing_decision` | `task`, `mode`, `provider`, `locality`, `fallback`, `reason`, `latency_ms` |
| `routing_attempt_failed` | `task`, `mode`, `provider`, `code`, `status` |
| `routing_exhausted` | `task`, `mode`, `reasons` |
| `chat` | `request_id`, `passages`, `cited`, `dropped`, `provider`, `locality` |
| `chat_generation_unavailable` | `request_id`, reasons |
| `ai_mode_changed` | `from`, `to`, `actor`, `request_id` |
| `knowledge_version_published` / `_announce_failed` | `version`, `previous`, `trigger` |
| `provider_request_rejected` | `provider`, rejected field types/locations (never values) |

## 4. Metrics

| Metric | Source today | Target |
|---|---|---|
| Latency p50/p95 per route | `duration_ms` in the request log | OTel span durations |
| Routing decisions | `GET /api/ai/providers` → `decisions` (`task\|provider\|outcome` counters) | OTel metrics (P2) |
| Provider health, circuit state | `GET /api/ai/providers` | dashboard panel |
| Queue depth | `/api/health` → `cv_model.message` (backlog) | — |
| Cache hit rate | not yet (M4 CAG) | — |
| GPU memory, tokens/s | not yet (vLLM `/metrics`) | — |

## 5. Alert thresholds (proposed)
- `aura` or `ollama` circuit `open` for longer than 5 min.
- More than 20% of chat responses in 15 min carry `generation_unavailable`.
- `/api/health` returns 503 for longer than 2 min.
- p95 `/api/chat` above 120 s on CPU, or 15 s on the L40S.

## 6. Following one `request_id` end to end
1. The client sends `X-Request-ID`, or the API generates `req_<hex>`. It comes back in the response header and in `meta.request_id`.
2. `grep request_id=<id>` in the API log gives the request line, the `chat` line and any `chat_generation_unavailable` line.
3. The routing lines for the same request fall between those timestamps. With tracing on, filter by `flame.request_id = <id>`: the trace shows each provider attempt.
4. AURA calls carry the same ID as `Idempotency-Key` and `X-Correlation-Id`, so AURA's own logs line up.
5. For analyses, `analysis_id` plays the same role in the worker log.

## Known limitations
No dashboards or alerting are deployed; the thresholds are proposals. Metrics are not exported as OTel metrics yet.

## Changelog
- 1.0.0 (2026-10-12): first guide; spans built in PR #14.
