# cv/

Flame-image analysis with OpenCV (PyTorch layer planned). **Owner:** Engineer 3. **Status:** baseline pipeline implemented (Otsu/contour segmenter, heuristic confidence); segmentation accuracy not yet evaluated (no ground-truth masks).

| Path | What it is |
|---|---|
| `flame_cv.py` | The pipeline: validate, letterbox preprocess, segment, features, confidence/quality flags, `AnalysisResult` (+ mask/overlay artifacts), intake manifest, analysis cache, evaluation runner and `flame_analysis_api_adapter` (imported by `apps/api` as `cv.flame_cv`) |
| `contracts/` | JSON Schemas (`analysis_result.schema.json`, `image_intake_schema.json`), an example payload, per-image results and `evaluation_report.json` |
| `notebooks/CVmodel_export.py` | Notebook export of the pipeline prototype; reference only, `flame_cv.py` is the source of truth |

Tests: `tests/cv/` (run `python -m pytest tests/cv` from the repo root). Training and evaluation data sources are in `docs/data/CV_IMAGE_SOURCES.md`. Split by **test**, not by frame, and never report temperature from RGB without calibration.

Planned: split `flame_cv.py` into `preprocessing/`, `inference/`, `training/`, `evaluation/` (MVP plan §14).
