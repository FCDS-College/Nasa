| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.1.0 | 2026-10-15 | C2, Model Router M1 | `tests/eval/ranking.py`, `tests/eval/master_pipeline.py` |

# E5-12: Local-vs-Cloud Evaluation Methodology

## 1. Scope & Tradeoff Dimensions

The platform supports dual deployment targets: **Cloud Scaled Services** (Google Cloud Vertex AI) and **Local Edge Nodes** (On-premises workstation / ISS compute). This document defines the formal comparative methodology across five trade-off dimensions:

| Dimension | Cloud Service (Gemini 1.5 Pro) | Local Model (Mistral-7b / Heuristics) | Selection Threshold / Policy |
|---|---|---|---|
| **Scientific Reasoning** | High (Deep cross-document synthesis) | Moderate (Single-document extractive) | Cloud preferred for multi-hop synthesis |
| **Air-Gap Compliance** | Incompatible (Requires internet) | **100% Compliant** | Local mandatory in air-gapped environments |
| **Inference Latency** | Network bound ($\approx 1000\text{ ms}$) | **Local memory bound ($\le 15\text{ ms}$)** | Local required for real-time safety shutoff |
| **Operational Cost** | Token-metered API billing | Fixed hardware capital cost | Local preferred for high-volume sweeps |
| **Determinism ($\sigma^2$)**| Temperature constrained | **Zero variance (Strict greedy/rules)** | Local preferred for repeatable regression gates|

---

## 2. Multi-Criteria Router Decision Rule

When routing queries via the central model router (Workstream M1):
1. **Safety & Classification Check**: If query contains `[CLASSIFIED_REF]` or offline flag is set $\to$ route to `local-offline-engine`.
2. **Complexity Tiering**:
   * Single-document lookup $\to$ route to `local-model` (low latency, zero API cost).
   * Cross-experiment comparative synthesis $\to$ route to `cloud-gemini-pro`.
3. **Fallback Policy**: Any network socket timeout ($> 3000\text{ ms}$) automatically reroutes execution to the local deterministic engine.
