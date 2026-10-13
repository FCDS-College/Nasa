# H-4: Hybrid AI API contracts

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review (sign-off: Belal E4, Eman E1) | 1.0.0 | 2026-10-12 | 2H Task 2, M1, M6, L-3 | `ai/providers/contracts/`, `docs/api/openapi.json` 0.2.0 |

## 1. Internal provider contracts (`ai/providers/contracts/`)

| Capability | Request | Response | Provider method |
|---|---|---|---|
| chat | `ChatRequest(messages, context: Passage[], max_output_tokens, temperature, timeout_s, idempotency_key, options)` | `ChatResponse(text, model, provider, cached, usage)` | `chat()` |
| structured | `StructuredRequest(chat: ChatRequest, schema: JSON Schema)` | `StructuredResponse(data: dict, model, provider, cached, usage)` | `generate_structured()` |
| embeddings | `EmbeddingRequest(texts, query: bool)` | `EmbeddingResponse(vectors, model, dimensions)` | `embed()` |
| reranking | `RerankRequest(query, documents: (id,text)[], top_k)` | `RerankResponse(scores: (id,score)[], model)` | `rerank()` |
| vision | `ImageAnalysisRequest(image_path, image_id, media_type, work_dir, mm_per_pixel, max_pixels)` | `ImageAnalysisResponse(analysis, provider, pipeline_version, artifacts)` | `analyze_image()` |
| video | `VideoAnalysisRequest(video_path, video_id, work_dir, sample_every_n_frames, max_frames)` | `VideoAnalysisResponse(frames, provider, pipeline_version, summary)` | `analyze_video()` (no adapter yet) |
| transcription | `TranscriptionRequest(audio_path, language)` | `TranscriptionResponse(text, segments, model, provider)` | `transcribe()` (no adapter yet) |

Every provider also has `info: ProviderInfo` (name, runtime, locality, capabilities, model, version, context_window, modalities) and `health(timeout_s) -> HealthStatus(state, latency_ms, detail, model_present)`.

**Passages** (`Passage(id, text, source)`) are evidence. Providers that have a DATA channel (AURA's `context`) put them there. The other providers receive them as a separate system message, fenced as untrusted data (`contracts/chat.py:render_context`). They are never concatenated into the user's question.

## 2. Normalized errors (`ProviderError`)

| Code | Meaning | Fallback-eligible | Retryable | Typical source |
|---|---|---|---|---|
| `not_configured` | missing endpoint/credentials, or 401/403 | yes | no | config |
| `unavailable` | unreachable, 5xx | yes | yes | network, server |
| `timeout` | no answer in time | yes | yes | slow model |
| `model_missing` | runtime up, model absent or corrupt | yes | no | `ollama pull` not run, empty fastembed cache |
| `resource_exhausted` | out of memory, 413/429/507 | yes | yes | big model on small host |
| `invalid_request` | we sent something wrong (4xx) | **no** | no | bug |
| `invalid_output` | answered, but not in the required shape | yes | no | weak model, schema drift |
| `egress_blocked` | blocked by `offline_only` | yes | no | mode |
| `unsupported` | capability not offered | yes | no | config |

`request_sent` is `false` only when the failure happened before the request left (connection refused, DNS, egress blocked).

## 3. Execution metadata (attached to every routed result)

`ExecutionMetadata` = `task`, `provider`, `runtime`, `model`, `version`, `locality` (`local|external`), `mode`, `fallback_used`, `routing_reason` (`preferred` or `fallback_after:<provider>:<reason>,…`), `latency_ms`, `attempts[] {provider, code}`.

Where it appears in the public API:
- `POST /api/chat` → `execution`;
- analysis → `pipeline.execution` (vision) and `interpretation.execution`.

## 4. Public API changes (contract 0.2.0; [CHANGELOG](../api/CHANGELOG.md))

| Endpoint | Auth | Purpose | Contract test |
|---|---|---|---|
| `POST /api/chat` (`x-aura-exclude`) | read | Grounded chat through the router | `apps/api/tests/test_chat.py`, `test_offline_routing.py` |
| `GET /api/ai/providers` (`x-aura-exclude`) | read | Mode, providers, health, circuit, decision counters | `test_offline_routing.py` |
| `PUT /api/admin/ai/mode` (`x-aura-exclude`) | write | Change mode; audited | `test_offline_routing.py::test_the_mode_change_needs_the_write_token_and_is_audited` |
| `GET /api/health` | read | `services.llm` / `services.aura` derived from the router; new `ai` block | `test_health.py` |

### Chat response, degraded mode

```json
{
  "answer": "No language model could write an answer right now, so here is the evidence Flame found for this question without a summary. Nothing below was generated.",
  "sources": [{"evidence_id": "…", "document_id": "…", "title": "…", "location": "p. 10"}],
  "model": {"provider": "flame", "name": "retrieval-only", "version": "n/a"},
  "execution": {"mode": "offline_only", "reasons": [{"provider": "ollama", "reason": "unavailable"}, {"provider": "aura", "reason": "egress_blocked"}]},
  "warnings": ["generation_unavailable"]
}
```

This is the actual body from the 2026-10-11 run with Ollama stopped, with IDs elided.

### Chat error codes

| Status | Code | When |
|---|---|---|
| 503 | `CHAT_UNAVAILABLE` | No language-model provider is configured or permitted in the current mode. The message names the mode, and `details.mode` gives it. |
| 429 | `RATE_LIMITED` | `FLAME_CHAT_RATE_LIMIT_PER_MINUTE` exceeded |
| 503 | `SEARCH_UNAVAILABLE` / `DATABASE_UNAVAILABLE` | retrieval failed |
| — | ~~`AURA_UNAVAILABLE` (502)~~ | Removed in 0.2.0; replaced by the degraded 200 above |

### Chat warnings

`no_matching_evidence`, `citations_not_in_retrieved_evidence_removed`, `answer_cites_no_evidence`, `generation_unavailable`, `model_fallback_used`.

## Known limitations
- Streaming responses are not part of the contract; every model call is a single request.
- `video` and `transcription` are contracts only.
- `model.version` is `unknown` for runtimes that don't report a model digest. The manifest (H-3) holds the authoritative version.

## Changelog
- 1.0.0 (2026-10-12): contracts as built in PR #14; public API 0.2.0.
