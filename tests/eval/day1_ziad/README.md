# Day 1 evaluation work (Engineer 5, Ziad): superseded

Archived as delivered on Day 1 (previously the untracked `Eng5/NASA/` folder). **Do not use these results as a quality gate.**

| File | What it does |
|---|---|
| `test_cases.jsonl` | 20 Q&A cases with hand-entered 1–5 scores |
| `smoke_test.ipynb` | Checks required fields in each case |
| `evaluator.ipynb` | Averages the stored scores against thresholds 4.0 / 4.5 / 4.0 |
| `rag_evaluator.ipynb` | Lists cases with any score below 4 |

**Why it is superseded:**
- The cases cover a fictional "movie fire ship", not the project corpus (BASS-II, FLEX, SAFFIRE-I, SPICE, NTRS papers).
- The scores are typed into the test file, so no system is ever measured.
- The format lacks the MVP plan §18 fields (split, expected evidence with locators, rubric version).

**Keep:** the test-design ideas ("no answer" cases TC_003/014/019, false premise TC_008, multi-source TC_011/020, visual TC_009/018) and the schema smoke check.

The redo plan is in `docs/plan/DAY2_TASKS.md` §7. Gold cases go to `datasets/evaluation/`; the harness becomes pytest modules in `tests/eval/`.
