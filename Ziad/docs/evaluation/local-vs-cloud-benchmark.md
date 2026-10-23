| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.3.0 | 2026-10-19 | C2, M1 | `ai/rag`, `tests/eval/ranking.py` |

# E5-12: Local-vs-Cloud Evaluation Methodology

## 1. Objective and Architectural Context

The NASA Advanced Scientific Intelligence Platform utilizes a hybrid intelligence architecture:
- **Local Edge Inference**: Powered by Ollama on Railway / air-gapped on-premises compute.
- **Cloud Model Routing**: Governed by the M1 Model Router connecting to high-capacity foundational models.

This document formalizes the rigorous comparative methodology across both execution contexts. Per evaluation requirements, **all comparative numbers are generated from benchmark execution runs (H-7 reports) and are never manually typed.**

---

## 2. Benchmark Protocol & Uniform Grounding

To guarantee scientifically defensible comparability:
1. **Identical Context Grounding**: Both local (Ollama) and cloud models must receive identical retrieved passage chunks and system prompts.
2. **Deterministic Sampling**: Generation temperature is set to $\tau = 0.0$ across all candidate sweeps.
3. **Repeated-Run Stability**: Minimum 3 repeated runs per query to evaluate output variance ($\sigma^2$) and token-level reproducibility.

---

## 3. Evaluation Dimensions & Key Performance Metrics

### 3.1 Quality Metrics
* **Faithfulness & Groundedness**: Atomic claim agreement against retrieved context passages.
* **Citation Precision & F1**: Accuracy of cited chunk IDs and document locators.
* **Abstention Correctness**: Refusal adherence on unanswerable and adversarial cases.

### 3.2 Operational Performance Metrics
* **Latency Profile**: Measurement of Time-to-First-Token (TTFT) and p50/p95 end-to-end request latency.
* **Resource Footprint**: Resident Set Size (RAM) and GPU VRAM allocation.
* **Cold-Start Penalty**: Elapsed time required to initialize models into operational memory.
* **Quantization Loss**: Degradation delta observed when compressing models (FP16 $\to$ INT4).

---

## 4. Formal Acceptance Thresholds (M1 Routing Gate)

| Metric | Local Candidate (Ollama) | Cloud Candidate (M1 Router) |
|---|---|---|
| **Faithfulness Rate** | $\ge 0.80$ | $\ge 0.90$ |
| **Citation F1 Score** | $\ge 0.70$ | $\ge 0.85$ |
| **Abstention Rate (Holdout Unanswerable)** | $100\%$ | $100\%$ |
| **Latency (p95)** | $\le 2000\text{ ms}$ | $\le 1500\text{ ms}$ |

*Execution results and comparative scorecards will be published in the H-7 evaluation report following production model deployment.*
