# Princess Weekly Progress Note

## Week of 2026-10-14

**Work**
- Added the baseline CLI (`python -m cv.flame_cv`), the offline manifest and verifier (with wheel checksums), and `docs/cv/offline-operation.md`.
- Consolidated the CNN prototype into `cv/cnn_pipeline.py` and renamed `pinn_pipline.py` to `pinn_pipeline.py`; both are marked unvalidated and optional.
- Added a video-contract fixture validated against `cv/contracts/video_analysis_result.schema.json`.
- Dropped unused `torch`/`torchvision` from `requirements.txt`.
- Implemented video ingestion, tracking/temporal metrics and a resumable `python -m cv.video_analysis` CLI; video schema is v1.3.0 (optional fields only). Added schema validation of all committed contract examples.
- Specs E3-6, E3-7, E3-8 and the E3-2 temporal section now describe the implemented behavior.

**Commits / PRs:** `2882127`..`2684c90` (offline tooling, CNN consolidation, docs); `ecd0f85`..`a154762` (video pipeline, tests, docs). PR: see the open PR from `Princess`.

**Metric run IDs:** none. No evaluation has been run against ground truth.

**Tests:** `python -m pytest tests/cv` passes (67 tests).

**Blockers:** ground-truth annotations and approved splits (Ziad); temporal metrics unevaluated against ground truth; committed contract examples still hold absolute `C:/FCDS` paths (regenerate from a real run); Python 3.14 limits TensorFlow to a release candidate.

**Document changes:** `docs/cv/offline-operation.md` (new), `video-ingestion.md`, `temporal-analysis.md`, `video-contract.md`, `measurement-definitions.md`, `pipeline.md`, `cv/README.md`, roadmap v0.3.0.