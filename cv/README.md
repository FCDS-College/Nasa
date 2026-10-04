# cv/

Flame-image analysis with PyTorch and OpenCV. **Owner:** Engineer 3. **Status:** contract defined, pipeline not implemented.

| Path | What it is |
|---|---|
| `contracts/analysis_result.json` | Example `AnalysisResult` payload: preprocessing, detection, segmentation, measurements, confidence and quality flags, and the scientific-interpretation label (MVP plan §10) |
| `pipeline.py` | Pipeline entry point (placeholder): Image → Validation → Preprocessing → Detection → Segmentation → Features → Measurements → Confidence → AnalysisResult |

Planned sub-folders: `preprocessing/`, `inference/`, `training/`, `evaluation/`.

Training and evaluation data sources are described in `docs/data/CV_IMAGE_SOURCES.md`. Split by **test**, not by frame, and never report temperature from RGB without calibration.
