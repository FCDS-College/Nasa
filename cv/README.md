# cv/

Flame-image analysis with OpenCV (PyTorch layer planned). **Owner:** Engineer 3. **Status:** auto-adaptive Otsu/contour pipeline implemented (v1.2.0); segmentation accuracy not yet evaluated (no ground-truth masks).

| Path | What it is |
|---|---|
| `flame_cv.py` | The pipeline: validate, letterbox preprocess, segment, features, confidence/quality flags, `AnalysisResult` (+ mask/overlay artifacts), intake manifest, analysis cache, evaluation runner and `flame_analysis_api_adapter` (imported by `apps/api` as `cv.flame_cv`) |
| `cnn_pipeline.py`, `pinn_pipeline.py` | **Unvalidated prototypes** (TensorFlow). Not registered models; see the roadmap scope boundaries |
| `configs/offline_manifest.json`, `utils/verify_offline_env.py` | Offline asset manifest and verifier (`python -m cv.utils.verify_offline_env --manifest cv/configs/offline_manifest.json`) |
| [docs/cv/offline-operation.md](../docs/cv/offline-operation.md) | **[E3-10]** Offline installation and verification |
| [docs/cv/pipeline.md](../docs/cv/pipeline.md) | **[E3-1]** Auto-adaptive pipeline stages, validation limits, configuration digests, and cache reuse. |
| [docs/cv/measurement-definitions.md](../docs/cv/measurement-definitions.md) | **[E3-2]** Measurement formulas, units, calibration, and quality flags. |
| [docs/cv/annotation-protocol.md](../docs/cv/annotation-protocol.md) | **[E3-3]** Annotation and dataset guidance. |
| [docs/cv/evaluation-report.md](../docs/cv/evaluation-report.md) | **[E3-4]** Baseline evaluation and limitations. |
| [models/otsu-contour-baseline/MODEL_CARD.md](models/otsu-contour-baseline/MODEL_CARD.md) | **[E3-5]** Baseline model card. |
| [docs/cv/video-ingestion.md](../docs/cv/video-ingestion.md) | **[E3-6]** Video ingestion specification. |
| [docs/cv/temporal-analysis.md](../docs/cv/temporal-analysis.md) | **[E3-7]** Temporal analysis specification. |
| [contracts/video_analysis_result.schema.json](contracts/video_analysis_result.schema.json) and [docs/cv/video-contract.md](../docs/cv/video-contract.md) | **[E3-8]** Video analysis result contract. |
| [docs/cv/performance.md](../docs/cv/performance.md) | **[E3-9]** Performance and GPU profile. |
| `contracts/` | JSON Schemas (`analysis_result.schema.json`, `image_intake_schema.json`), an example payload, per-image results and `evaluation_report.json` |
| `notebooks/CVmodel_export.py` | Notebook export of the pipeline prototype; reference only, `flame_cv.py` is the source of truth |

Run the baseline: `python -m cv.flame_cv [image] [--out-dir cv/output]` (synthetic flame if no image).

Tests: `tests/cv/` (run `python -m pytest tests/cv` from the repo root). Training and evaluation data sources are in `docs/data/CV_IMAGE_SOURCES.md`. Split by **test**, not by frame, and never report temperature from RGB without calibration.

Planned: split `flame_cv.py` into `preprocessing/`, `inference/`, `training/`, `evaluation/` (MVP plan §14).