# tests/

Automated tests and evaluation gates. **Quality lead:** Engineer 5; every component owner adds tests for their own code.

| Folder | What goes here |
|---|---|
| `unit/` | pytest unit tests for `ai/rag/`. Run from the repo root: `python -m pytest` |
| `integration/` | Cross-system checks, e.g. `aura_blueprint_dryrun.py` (AURA requirement AR-1) |
| `eval/` | Evaluation notebooks and test cases. `day1_ziad/` archives the superseded Day 1 work; `day2_ziad/` holds the Day 2 evaluation framework. Run outputs go in `eval/runs/<run_id>.jsonl` |

Planned sub-folders (MVP plan §14): `ai/`, `rag/`, `cv/`. Gold evaluation sets (versioned JSONL, expectations only) live in `datasets/evaluation/` (MVP plan §18).
