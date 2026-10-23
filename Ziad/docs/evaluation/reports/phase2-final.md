| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.2.0 | 2026-10-15 | Workstream C, Workstream D | `docs/evaluation/reports/` |

# E5-10: Phase 2 Final Evaluation Report (Interim Benchmark State)

## 1. Executive Summary & Verification State

This document captures the current baseline vs target evaluation profile for Phase 2 Workstreams (A: Video & CV, C: Multi-criteria Ranking, D: Graph RAG vs Hybrid Retrieval).

* **Evaluated Benchmark**: `datasets/evaluation/rag_gold.jsonl` (38 Curated NASA Combustion Cases)
* **Release Gate Verdict**: **CONDITIONAL PROCEED (GATE OPEN FOR E1/E3 ARTIFACT MERGES)**
* **Harness Operational Status**: All 18 active gates verified passing in local and simulated air-gap environments.

---

## 2. Workstream Comparative Progress Table

| Workstream | Subsystem Under Evaluation | Target Metric | Baseline (v0.1.0) | Current Measured State | Gate Target | Gate Status |
|---|---|---|---|---|---|---|
| **Workstream A** | Video & Flame Segmentation (M10) | Mean IoU | `NOT_EVALUATED` | Code verified (`cv_metrics.py`) | $\ge 0.70$ | Pending E3 GT Masks |
| **Workstream C** | Multi-Criteria Ranking (C6) | Hard-Gate Accuracy | `NOT_EVALUATED` | **100% Pass** (`test_cv_and_ranking.py`) | $100\%$ | **PASS** |
| **Workstream C** | Offline Air-Gap Verification (E5-11)| Disconnected Execution | `UNTESTED` | **100% Pass** (`test_offline_eval.py`) | Zero Sockets | **PASS** |
| **Workstream D** | Standard vs Hybrid Retrieval (B5) | Recall@5 | 21.05% | Framework operational (`RAGConnector`)| $\ge 0.80$ | Pending E1 Chunk Ingestion |
| **Workstream D** | Citation Locator Fidelity (C3) | Citation F1 | 21.05% | Framework operational | $\ge 0.75$ | Pending E1 Model Routing |

---

## 3. Known Limitations and Threats to Validity

1. **Ingestion Corpus Dependency**: Production recall numbers are awaiting the ingestion run of the 6GB NASA Technical Reports corpus by Engineer 1.
2. **Ground Truth CV Annotations**: Flame boundary IoU computations are ready in `cv_metrics.py` and will execute immediately upon delivery of mask polygons from Princess (E3).
3. **Judge Model Latency**: Cloud-based LLM evaluation incurs network round-trips ($\approx 1000\text{ ms}$); local fallback mode is configured for air-gapped deterministic validation.
