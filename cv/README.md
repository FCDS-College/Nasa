# cv/

Flame-image analysis with OpenCV (PyTorch layer planned). **Owner:** Engineer 3. **Status:** auto-adaptive Otsu/contour pipeline implemented (v1.2.0); segmentation accuracy not yet evaluated (no ground-truth masks).

| Path | What it is |
|---|---|
| `flame_cv.py` | The pipeline: validate, letterbox preprocess, segment, features, confidence/quality flags, `AnalysisResult` (+ mask/overlay artifacts), intake manifest, analysis cache, evaluation runner and `flame_analysis_api_adapter` (imported by `apps/api` as `cv.flame_cv`) |
| `telemetry_ocr.py` | Telemetry-banner OCR: per-field ROIs, range validation, multi-frame voting, exact-match accuracy helper |
| `video_embedding.py` | Label-free temporal model: frozen ResNet18 embeddings (CUDA/AMP) + GRU next-embedding head; reports val MSE vs copy-previous baseline (not accuracy) |
| `hf_space/` | Docker Space endpoint for remote `flame_cv.py` inference; deployment and worker configuration are documented in `apps/api/README.md` |
| `video_training.py` | Trains/evaluates video-level models on the 17 PSI-25 videos with labels from the experimental table (initial O2 %, fuel family); leave-one-test-out vs baselines; writes `contracts/training_report*.json` (`python -m cv.video_training --arch resnet18`) |
| `notebooks/models.ipynb` | Thin driver for the two modules above |
| `overlay_mask.py` | Finds burned-in text overlays (telemetry banner, timestamps) across a video and masks them before segmentation, so the banner is never measured as a flame. Steady flames are not masked. See [docs/cv/video-ingestion.md §5](../docs/cv/video-ingestion.md#5-overlay-exclusion-pipeline-cv-video-v110) |
| `video_ingestion.py`, `temporal_analysis.py`, `video_analysis.py` | **[E3-6, E3-7, E3-8]** Video ingestion (validation, metadata, stable frame IDs, sampling, VFR normalization), tracking and temporal metrics, and the resumable end-to-end `python -m cv.video_analysis <video>` CLI. Temporal metrics are unevaluated against ground truth |
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

Run a video: `python -m cv.video_analysis path\to\video.mp4 --sample-every 30` (resumes automatically after interruption).

Run the baseline: `python -m cv.flame_cv [image] [--out-dir cv/output]` (synthetic flame if no image).

Tests: `tests/cv/` (run `python -m pytest tests/cv` from the repo root). Training and evaluation data sources are in `docs/data/CV_IMAGE_SOURCES.md`. Split by **test**, not by frame, and never report temperature from RGB without calibration.

Planned: split `flame_cv.py` into `preprocessing/`, `inference/`, `training/`, `evaluation/` (MVP plan §14).