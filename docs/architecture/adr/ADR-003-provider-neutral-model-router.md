# ADR-003: Provider-neutral model router

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Lead; Eman (E1) and Ziad (E5) affected

## Context
At the 2026-10-10 audit, Flame had no language model of its own. `/api/chat` returned `503 CHAT_UNAVAILABLE` unless AURA (on Railway) was enabled. Image interpretation had the same dependency. The embedder downloaded its weights from Hugging Face on first use. MVP §5.3 and §11 require provider independence (M1). Sub-phase 2H requires the platform to keep working without internet.

## Decision
One router (`ai/routing/router.py`) in front of typed provider contracts (`ai/providers/contracts/`). The pieces are:

- **Contracts:** chat, structured output, embeddings, reranking, vision, video and transcription. They use stdlib dataclasses and `Protocol`s, normalized `ProviderError` codes, and `ExecutionMetadata`.
- **Adapters:**
  - local: `ollama`, `vllm`, `llamacpp`, `fastembed`, `cross_encoder`, `flame_cv`;
  - external: `aura`, `hf_space`.

  "Local" means on the same, possibly disconnected, network, not on the same machine.
- **Execution modes** (`FLAME_AI_EXECUTION_MODE`):
  - `cloud_preferred`;
  - `local_first` (default);
  - `offline_only`, which refuses external providers before any socket opens, probes included.
- **Policies:**
  - a circuit breaker per provider;
  - cached, bounded health probes kept off the request path;
  - fallback only on fallback-eligible codes;
  - no re-send of a non-idempotent request that may have arrived;
  - one try per provider per request;
  - capability *and* modality matching, so a vision task never goes to a text model.
- **Single wiring point:** `apps/api/flame_api/ai_runtime.py`. It is the only module that constructs concrete providers.

## Alternatives considered
- **LiteLLM or a similar SDK.** It brings a large dependency and hosted-vendor defaults, its offline guarantees are hard to audit, and it does not cover vision/CV routing. Rejected.
- **Route inside AURA.** That keeps AURA as a hard dependency, which is the problem M1 removes. Rejected (ADR-004).
- **One adapter per call site.** This was the status quo, and it is why chat needed AURA. Rejected.

## Consequences
- Changing which model answers is configuration only (`FLAME_OLLAMA_*`, `FLAME_VLLM_*`, `FLAME_AURA_*`).
- Responses carry `execution` metadata: provider, model, locality, mode, fallback and reason (H-4).
- The router keeps per-process state (circuit, health cache). Each API replica and the worker decide independently. The mode itself is shared through `audit_event` (ADR-009 / H-2 §5).
- Model quality is a separate question: the router makes any model replaceable, and H-7 must still pick one. The first measured CPU model (`qwen2.5:3b`, about 50–78 s per answer on 4 CPUs) is a feasibility baseline, not a quality choice.

## Links
[H-2 architecture](../../hybrid-ai/PHASE_2_HYBRID_AI_ARCHITECTURE.md), [H-4 contracts](../../hybrid-ai/PHASE_2_HYBRID_AI_API_CONTRACTS.md), `tests/unit/test_model_router.py`, `apps/api/tests/test_offline_routing.py`.
