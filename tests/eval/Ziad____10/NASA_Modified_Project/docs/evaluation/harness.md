| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.2.0 | 2026-10-15 | M11 | `run_evaluation.py`, `tests/eval/` |

# E5-4: Harness User Guide

## 1. Quick Start & Prerequisites

Install required evaluation dependencies:
```bash
pip install -r requirements.txt
```

---

## 2. Complete Runnable Commands by Subsystem

The harness provides deterministic single-line commands to execute and verify each subsystem:

### 2.1 Complete Automated Gate Suite (All 4 Subsystems)
```bash
pytest tests/eval/ -v --durations=10
```

### 2.2 RAG Information Retrieval & Grounding Suite
```bash
# Run RAG IR metrics and provenance isolation gates
pytest tests/eval/test_provenance.py tests/eval/test_rag_metrics.py -v
```

### 2.3 Computer Vision Flame Segmentation Suite (Workstream M10)
```bash
# Run CV mask metrics (IoU, Dice, Precision, Recall)
pytest tests/eval/test_cv_and_ranking.py -k "cv" -v
```

### 2.4 LLM Scientific Reasoning & Multi-Criteria Ranking Suite (Workstream C2 & C6)
```bash
# Run ranking and model hard-gate filters
pytest tests/eval/test_cv_and_ranking.py -k "rank" -v
```

### 2.5 API Contract Test Suite (Workstream C1 Backend)
```bash
# Run API endpoint contract verification stubs
pytest tests/eval/test_api_contracts.py -v
```

---

## 3. End-to-End Evaluation Runner CLI

To execute the full 31-case benchmark against the RAG connector and generate artifacts:

```bash
# Local testing mode with mock connector
python run_evaluation.py --model mock --data datasets/evaluation/rag_gold.jsonl --out evaluation_report.json

# Live backend mode targeting the production FastAPI service
python run_evaluation.py --model api --api-url http://localhost:8000 --data datasets/evaluation/rag_gold.jsonl
```

### Rendering Run Output into Reports
Following the principle: **"Numbers are generated, never typed"**:
```bash
python render_report.py
```
This renders `evaluation_report.json` into:
1. `docs/evaluation/reports/baseline-v0.1.0-mvp.md` (Markdown Baseline Scorecard)
2. `scorecard.html` (Interactive Dark-Mode Visual Dashboard)

---

## 4. Run Metadata & Provenance Schema (§18)

Every run outputs an immutable provenance block:
```json
{
  "provenance": {
    "git_commit": "e.g., f9ee52f",
    "dataset_sha256": "37f48b...",
    "timestamp": "2026-10-15T13:00:00Z",
    "scorer_version": "v2.0",
    "model_provider": "gemini-pro / local-fallback",
    "prompt_version": "prompt-v2.0",
    "hardware": "Windows-AMD64-...",
    "rubric_version": "v2.0"
  }
}
```

---

## 5. Regression Detection Protocol in CI

Continuous evaluation runs on GitHub Actions via `.github/workflows/eval.yml`:
1. **Critical Failure**: Any hallucination on holdout adversarial cases halts deployment immediately with non-zero exit code (`exit 1`).
2. **Tolerance Limit**: Drops exceeding $\Delta \text{Recall@5} < -0.02$ or $\Delta \text{MRR} < -0.02$ fail the build.
