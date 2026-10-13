# Princess Weekly Progress Note

## Week of 2026-10-14

**Work**
- Added the baseline CLI (`python -m cv.flame_cv`), the offline manifest and verifier (with wheel checksums), and `docs/cv/offline-operation.md`.
- Consolidated the CNN prototype into `cv/cnn_pipeline.py` and renamed `pinn_pipline.py` to `pinn_pipeline.py`; both are marked unvalidated and optional.
- Added a video-contract fixture validated against `cv/contracts/video_analysis_result.schema.json`.
- Dropped unused `torch`/`torchvision` from `requirements.txt`.

**Commits / PRs:** to be filled in when the branch is pushed.

**Metric run IDs:** none. No evaluation has been run against ground truth.

**Tests:** `python -m pytest tests/cv` passes (37 tests).

**Blockers:** ground-truth annotations and approved splits (Ziad); video ingestion not implemented; Python 3.14 limits TensorFlow to a release candidate.

**Document changes:** `docs/cv/offline-operation.md` (new), `docs/cv/pipeline.md`, `cv/README.md`.