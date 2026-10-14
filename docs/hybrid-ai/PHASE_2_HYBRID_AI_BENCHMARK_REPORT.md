# H-7: Hybrid AI benchmark report

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas); harness Ziad (E5) | Draft: first feasibility numbers only | 0.1.0 | 2026-10-12 | 2H Task 4, C2 | Ziad's harness (`tests/eval/`), `datasets/evaluation/` |

## 1. Method (to run in Ziad's harness)
- **Same benchmark for every candidate:** `datasets/evaluation/rag_gold.jsonl` (M11), grown from 6 items to the size fixed in Week 1, with dev, validation and holdout splits. Report the dataset checksum.
- **Per capability and candidate (local vs AURA):**
  - quality: grounded-answer correctness, citation precision and recall, abstention on missing-evidence items, prompt-injection cases;
  - latency: p50 and p95, cold and warm;
  - throughput;
  - peak RSS / VRAM;
  - quantization loss (Q4 vs FP16 where both run).
- **Run metadata:** commit, benchmark checksum, hardware, runtime version, model version and checksum (H-3), prompt version.

## 2. Verdict criteria (proposed, for Ziad's sign-off)
- **Local CPU model:** acceptable as the offline fallback if it abstains correctly on ≥ 90% of missing-evidence items and never cites outside the retrieved set. That second check is enforced by code, so it should be 100%.
- **Primary model:** the candidate with the best holdout correctness inside its latency budget.

## 3. First feasibility measurements (not the benchmark)

2026-10-11, 4 vCPU / 15 GiB, no GPU. Commit: working tree of `2afbc37`.

| Candidate | Capability | n | Latency | Notes |
|---|---|---|---|---|
| `qwen2.5:3b-instruct-q4_K_M` (Ollama 0.5.7, CPU) | `chat.answer` | 3 | 77,774 ms cold; 50,042 and 53,682 ms warm | 3/3 valid JSON on the first try. 0 citations outside the retrieved set. 1/3 answers only echoed a title; 1/3 abstained although cited p. 10 discusses oxygen effects. |
| `bge-small-en-v1.5` (fastembed 0.9.0, CPU) | `embed.documents` | 37 chunks | 9.5 s wall-clock for the whole build, including model load | — |

These are **not** a benchmark (n = 3, no gold labels). They only show that the CPU path is feasible. At this latency, a 500-token answer fits inside `FLAME_LLM_TIMEOUT_S = 180`.

## 4. Pending runs

| Run | Owner | Needs |
|---|---|---|
| Local CPU vs AURA on the gold set | Ziad + Lead | the M11 harness and gold set |
| vLLM 7B-AWQ on the L40S | Lead | L40S access |
| Q4 vs FP16 quantization loss (7B) | Lead | L40S |
| Reranker on/off retrieval metrics | Eman | M2 wiring |

## Known limitations
No verdict can be given yet, and H-3 statuses stay `candidate` until §4 runs.

## Changelog
- 0.1.0 (2026-10-12): method, criteria and first feasibility numbers.
