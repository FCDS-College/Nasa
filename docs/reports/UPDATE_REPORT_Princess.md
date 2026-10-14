# Update Report: Princess (Engineer 3, Computer Vision / PyTorch)

**Reviewed:** `main` @ `f9ee52f` · **Basis:** MVP plan §10, §15 (Engineer 3), §16 daily table, §22
**Verification:** `cv/flame_cv.py` tests: 22 passed (`python -m pytest tests/cv` from the repo root). The API's CV adapter tests (`apps/api/tests/test_cv_adapter.py`) also pass.

## Verdict: 7.5 / 10 against the MVP scope (strongest delivery on the team; accuracy is still unproven)

## Plan requirements vs. delivered

| Plan item (Engineer 3) | Day | Status | Evidence |
|---|---|---|---|
| CV IO / `AnalysisResult` contract | 1 | Done | `cv/contracts/analysis_result.schema.json` (JSON Schema 2020-12, generated from the pydantic models), example payload |
| Image dataset intake specification | 2 | Done | `contracts/image_intake_schema.json`, `IntakeManifest`, group-aware dev/val/test split (`split_for_group`) |
| Preprocessing prototype | 3 | Done | Deterministic EXIF-aware letterbox preprocessing, original never modified, versioned |
| Baseline detector choice, dataset manifest | 4 | Done | Otsu + contour baseline, named and versioned in every result |
| Segmentation prototype | 5 | Done | Mask + overlay artifacts written per image |
| Analysis request/response stub | 6 | Done | `analyze_image_safe`, typed error hierarchy, `flame_analysis_api_adapter` consumed by `apps/api/flame_api/worker.py` |
| Validation, detection baseline, artifact storage | 8 | Done | MIME/size/pixel/decode limits as in §19 |
| Segmentation, geometry/colour features, confidence flags | 9 | Done | Geometry (area, perimeter, bbox in **original** pixels), colour stats, computed (not hard-coded) quality flags |
| API adapter, reproducible artifacts | 10 | Done | Adapter live in the API; results carry config digest and checksums |
| Structured output validation | 11 | Done | Every result is validated against the pydantic model |
| Analysis cache manifest | 12 | Done | `AnalysisCache`, key = input sha + pipeline/preprocess/segmenter/config versions |
| CV evaluation runner | 13 | Partial | `run_cv_evaluation` runs and writes `contracts/evaluation_report.json`, but **segmentation is `NOT_EVALUATED`**: no ground-truth masks, acceptance threshold is `null` |
| CV output/model audit | 14 | Not done | No audit report |

## What was good
- Follows the plan's integrity rules: observed/measured/estimated/inferred labels on result blocks, "no temperature from RGB", confidence basis stated as `heuristic_uncalibrated`.
- Cache invalidation is version-aware; the pipeline has a clean error taxonomy.
- 22 behavioural tests that run without a GPU or network.

## Defects found (and what was done)
| # | Finding | Action |
|---|---|---|
| 1 | `cv/README.md` said "pipeline not implemented" and pointed to a notebook and `pipeline.py` that no longer exist. | **Rewritten** |
| 2 | `cv/CVmodel.PY` (1238 lines) was an upper-case-extension notebook export sitting next to the real module. | **Moved** to `cv/notebooks/CVmodel_export.py` |
| 3 | `cv/test_flame_cv.py` lived inside the source folder and used `from flame_cv import`. | **Moved** to `tests/cv/` with `from cv.flame_cv import` (the same import path the API uses) |
| 4 | Committed result JSON (`cv/contracts/*.json`, `results/*.json`) embeds **absolute paths from one machine** (`C:/FCDS/Nasa/datasets/...`) in `derivedUri`, `maskUri`, `imageDir`. They do not resolve on any other machine, which breaks the plan's "provenance from result to artifact". | Not changed (regenerated output). Store repo-relative URIs and regenerate. |
| 5 | Detector confidence (0.985 on every sample) is an uncalibrated heuristic, and the report shows `saturationClipping` on 100% of the samples. This is correctly labelled, but it is not evidence of accuracy. | Not changed. |
| 6 | The sample set is 10 frames from one ISS-018 sequence; no ground-truth masks. | See next steps. |
| 7 | `flame_cv.py` is one 1,086-line module; §14 asks for `preprocessing/ inference/ training/ evaluation/`. | Not changed: `apps/api` imports `cv.flame_cv`, so it is deferred to avoid breaking the worker. |

## Next steps (priority order)
1. Hand-label masks for 20-30 frames across at least 3 different tests (split by test, not frame) and report IoU/F1 with a stated acceptance threshold (Ziad's Day 9 test cases depend on this).
2. Regenerate `contracts/` with repo-relative URIs and add a test that fails when a committed artifact path is absolute.
3. Write the Day 14 CV model/output audit (versions, digests, known failure modes, e.g. saturation).
4. Split `flame_cv.py` into the §14 sub-packages in one PR, keeping a `cv/flame_cv.py` re-export so the API import stays valid.
5. Add the PyTorch learned segmenter behind the same contract once labelled data exists; keep the Otsu baseline as the reference.
