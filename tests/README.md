# tests/

Automated tests and evaluation gates. **Quality lead:** Engineer 5; every component owner adds tests for their own code.

| Folder | What goes here |
|---|---|
| `unit/` | pytest unit tests for `ai/rag/` (retrieval, chunking, citations, DTOs) and the model router (`test_model_router.py`) |
| `cv/` | pytest tests for `cv/flame_cv.py` |
| `integration/` | Cross-system checks, e.g. `aura_blueprint_dryrun.py` (AURA requirement AR-1) |
| `eval/` | Evaluation framework (Engineer 5): scripts (`evaluator.py`, `audit_logger.py`, `master_pipeline.py`), notebooks, `test_cases.jsonl`, run outputs (`audit_log.json`, `evaluation_report.json`, `experiment_history.json`) and `test_provenance.py`. Run the scripts and notebooks from inside `eval/` (they use relative paths). `archive/` holds superseded Day 1-3 work |

Gold evaluation sets (versioned JSONL, expectations only) and their schema live in `datasets/evaluation/` (MVP plan §18). The provenance checklist is `docs/evaluation/provenance_checklist.md`.

**One command for everything:** `python -m pytest` from the repo root runs `tests/` and `apps/api/tests` together (`pytest.ini`; see [docs/operations/CI_CD.md](../docs/operations/CI_CD.md)). A single folder still works: `python -m pytest tests/unit`.
