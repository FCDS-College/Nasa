# H-3: Local model registry

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review (sign-off: Ziad E5, Princess E3) | 1.0.0 | 2026-10-12 | 2H Task 4, C1, M8 | `ai/routing/model_manifest.json`, `apps/api/flame_api/seed.py:seed_models`, table `model` |

**Source of truth.** [`ai/routing/model_manifest.json`](../../ai/routing/model_manifest.json) is validated by `ai/routing/registry.py:load_manifest`, which rejects unknown keys, duplicates and missing required fields. `python -m flame_api.seed` loads it into the `model` table, the C1 model registry (no second registry). Status values:
- `approved`: in use and evaluated;
- `candidate`: wired, but not benchmarked in H-7;
- `retired`.

## Registry

| model_id | Capability | Runtime | Version / tag | Quantization | License | Checksum (sha256) | Size on disk | RAM / VRAM | CPU-only | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| <a id="general-llm"></a>`ollama:qwen2.5:3b-instruct-q4_K_M` | structured / chat | Ollama 0.5.7 | `qwen2.5:3b-instruct-q4_K_M`, Ollama digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b` (m) | Q4_K_M GGUF | Qwen Research License (3B) | Pending: the GGUF blob sha256 (see procedure §2) | 1,929,912,432 B (m) | ~3 GB RAM (e) | yes | candidate |
| <a id="gpu-llm"></a>`vllm:Qwen/Qwen2.5-7B-Instruct-AWQ` | structured / chat | vLLM (L40S) | HF repo revision: Pending | AWQ 4-bit | Apache-2.0 | Pending | Pending | ~8 GB VRAM + KV (e) | no | candidate |
| <a id="embeddings"></a>`fastembed:BAAI/bge-small-en-v1.5` | embeddings | fastembed 0.9.0 | `Qdrant/bge-small-en-v1.5-onnx-Q@aa8f8b060edb00e03bfdd08813a2949946c8ba55` | ONNX quantized | MIT | `51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431` (m) | 66,465,124 B model; 67,181,750 B cache (m) | ~300 MB (e) | yes | approved |
| <a id="reranker"></a>`sentence-transformers:cross-encoder/ms-marco-MiniLM-L-6-v2` | reranking | sentence-transformers | Pending | — | Apache-2.0 | Pending | Pending | ~400 MB (e) | yes | candidate |
| <a id="computer-vision"></a>`flame_cv:cv-opencv-v1.2.0-auto` | vision | OpenCV | `cv-opencv-v1.2.0-auto` (v1.1.0 kept in `cv/oldversion/`) | — | project code | n/a (code; git commit is the version) | — | ~0.5 GB / 50 MP (e) | yes | approved |
| `hf_space:flame_cv` | vision (external) | HF Space | same pipeline | — | project code | n/a | — | — | yes | approved |
| `aura:orchestrator` | structured (external) | AURA | whatever AURA routes to (reported per response) | — | self-hosted | n/a | — | — | — | approved |

(m) = measured in this container on 2026-10-11. (e) = estimate from published sizes, to be replaced by H-7 measurements.

**Licence note.** `qwen2.5:3b` is under the Qwen Research License, not Apache-2.0 like the 7B. It is acceptable for this research project but must be reviewed before any commercial use. That is one reason it is only a *candidate*.

## 1. Why these candidates

Selection rule (§8.5 Task 4): one reliable model per critical capability, chosen by benchmark, not popularity. H-7 has not run yet, so these are **candidates with stated reasons**, not selections:

- **`qwen2.5:3b-instruct-q4_K_M`.** The smallest instruction model that supports Ollama's JSON-schema `format`. AURA already runs it in production on CPU, which makes it a known-feasible CPU baseline. Measured here: it answers a grounded question in 50–78 s on 4 vCPUs. In 1 of 3 test answers it only echoed a title (H-7 §3). Its quality is unproven.
- **`Qwen2.5-7B-Instruct-AWQ`.** The same weights as AURA's GPU Space, so local-vs-AURA comparisons in H-7 isolate the serving path.
- **`bge-small-en-v1.5`.** Already the production index model (ADR-002). Replacing it means a full re-index.

## 2. Download and verification procedure

Run this while connected, on the machine or volume that will go offline.

```bash
# Embeddings: download, then verify offline (HF_HUB_OFFLINE=1) and print sha256 of every ONNX file
python -m ai.providers.local.fastembed_embeddings prepare --cache-dir "$FLAME_EMBEDDING_CACHE_DIR"
python -m ai.providers.local.fastembed_embeddings verify  --cache-dir "$FLAME_EMBEDDING_CACHE_DIR"
# Compare with the manifest's sha256 for fastembed:BAAI/bge-small-en-v1.5.

# Local LLM (Compose)
docker compose -f infrastructure/compose.yaml --profile local-llm up -d ollama
docker compose -f infrastructure/compose.yaml --profile local-llm-setup run --rm ollama-pull
docker compose -f infrastructure/compose.yaml exec ollama ollama show --modelfile qwen2.5:3b-instruct-q4_K_M | head
# The GGUF blob is named by its sha256 under the volume's /root/.ollama/models/blobs/: record it in the manifest.
```

After any change to the manifest, run `python -m flame_api.seed` so the `model` table matches.

## 3. Startup health checks, limits and warm-up

- **Health.** `/api/ai/providers` and `/api/health` probe each permitted provider (bounded at ≤2 s, cached for 15 s):
  - Ollama checks that the model is in `/api/tags`;
  - vLLM and llama.cpp check that the model is in `/v1/models`;
  - fastembed checks that ONNX files are in the cache.

  A missing model is reported as `down` / `model_missing`.
- **Resource limits.** Compose sets no memory limit on `ollama` yet. Set `deploy.resources.limits.memory` per host (H-6). An out-of-memory error from the runtime is surfaced as `resource_exhausted`, and the router moves on.
- **Warm-up and loading.**
  - `OLLAMA_KEEP_ALIVE=30m` (Compose) and `keep_alive` per request keep the model resident. The measured cold start added about 25 s over the warm calls.
  - fastembed loads once per process (`FastEmbedProvider._load`).

## Known limitations
- Most checksums and every H-7-backed reason are Pending until the L40S and benchmark runs.
- The C1 model cards (Ziad) are not written yet. `model_card` points at this document's anchors until they are.

## Changelog
- 1.0.0 (2026-10-12): first registry; embedding checksum and Ollama size measured.
