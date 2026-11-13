| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 0.1.0 | 2026-10-14 | E3-10, H-1, H-3 | `cv/configs/offline_manifest.json`, `cv/utils/verify_offline_env.py`, `cv/flame_cv.py` |

# CV Offline Operation

## 1. Scope

Only the Otsu/contour baseline (`cv/flame_cv.py`) and the video pipeline built on it are supported capabilities. The CNN (`cv/cnn_pipeline.py`) and PINN (`cv/pinn_pipeline.py`) modules are **unvalidated prototypes**: they are optional in the manifest and are not registered models. Video ingestion, temporal analysis and resumable processing are implemented (see [video-ingestion.md](video-ingestion.md)). Audio transcription is implemented but optional and off by default (`FLAME_TRANSCRIPTION_ENABLED`); with no cached model it reports `model_missing` and never downloads offline ([audio-transcription.md](audio-transcription.md)).

The baseline uses no network, no external CV provider and no downloaded weights. RGB values do not establish calibrated temperature; a local language model may interpret documented measurements but must not replace or override CV computation.

## 2. Dependencies

Listed in the root `requirements.txt`: numpy, scipy, opencv-python-headless, pillow and pydantic (used by `flame_cv.py`), tensorflow (prototypes only), jsonschema and pytest.

Known gap: the recorded wheels were built on Python 3.14, where TensorFlow is only available as a release candidate. Use Python 3.12 with a stable TensorFlow 2.x for reproducible installs.

## 3. Procedure (run from the repository root)

```powershell
# On a networked machine
pip download -r requirements.txt -d cv/weights/offline_packages/ --retries 10 --timeout 60
python -m cv.utils.verify_offline_env --manifest cv/configs/offline_manifest.json --write-checksums

# On the air-gapped machine
pip install --no-index --find-links=cv/weights/offline_packages/ -r requirements.txt
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
python -m cv.utils.verify_offline_env --manifest cv/configs/offline_manifest.json --check-packages
python -m cv.flame_cv
```

`cv/weights/` and `cv/output/` are git-ignored. The checksum file `cv/configs/offline_packages.sha256` is committed; regenerate it whenever the wheels change.

## 4. Verification behavior

| Condition | Result |
|---|---|
| Required asset missing, smaller than `minSizeBytes`, or `sha256` mismatch | `[FAIL]`, exit code 1 |
| Optional asset missing or invalid | `[WARN]`, exit code unaffected |
| Wheel missing, modified or unlisted (with `--check-packages`) | `[FAIL]`, exit code 1 |
| Manifest missing | `[ERROR]`, exit code 1 |

Image-analysis failures are returned as controlled `ErrorResponse` payloads (`analyze_image_safe`); the `python -m cv.flame_cv` CLI exits 1 for them.

## 5. Resumable video processing

`python -m cv.video_analysis <video> --out-dir cv/output/video [--sample-every N] [--max-frames M]` analyzes a local video with no network access.

- Each analyzed frame is appended to `<out-dir>/<videoId>/frames.jsonl` and flushed, and `job.json` holds the job state: `RUNNING` while in progress and `COMPLETE` when `summary.json` has been written. A killed process leaves the job `RUNNING`.
- Re-running the same command resumes: completed frames are read from the checkpoint and only the remaining frames are analyzed. A truncated last line is discarded and that frame is recomputed. A finished job is reassembled from the checkpoint without re-analysis.
- The checkpoint is keyed by a job digest (video checksum, pipeline versions, video and CV configuration). If any of these change, the stale checkpoint is discarded; `--no-resume` forces a fresh run.
- Error behavior: unsupported, oversize, over-long or corrupt videos return a controlled `ErrorResponse` (exit code 1 from the CLI); a failed frame is recorded as `UNCERTAIN` with its error code and does not abort the video.
- Scope: this is recovery within the CV job. Restart handling by the API worker and job queue is owned by the Lead and is not exercised here. `tests/cv/test_video_pipeline.py` simulates an interruption and verifies the resume.

## Known limitations and failure modes
- Checksums cover Python wheels only; there are no model weights to checksum for the baseline.
- OpenCV/TensorFlow builds, codecs and CPU-only viability for the prototypes are not benchmarked.
- Restart recovery is tested only as an in-process simulated interruption, not as an application restart under the Lead's job infrastructure. Video decoding depends on the codecs in the local OpenCV build, which are not inventoried here.
- No CPU-only video throughput has been measured.
- The verifier checks file presence, size and checksums, not that imports succeed.

## Changelog

- **0.2.0 (2026-10-14):** Added the resumable video processing procedure.
- **0.1.0 (2026-10-14):** Initial offline procedure and verifier behavior.