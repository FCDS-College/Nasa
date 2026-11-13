| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.1.0 | 2026-10-14 | A1, E3-6 | `cv/video_ingestion.py`, `cv/video_analysis.py` |

# Video Ingestion Specification (A1)

Implemented in `cv/video_ingestion.py` (`probe_video`, `iter_frames`) and driven by `cv/video_analysis.py`.

## 1. Scope and Accepted Formats
- **Containers:** `.mp4`, `.avi`, `.mov`. Anything else raises `UNSUPPORTED_MEDIA_TYPE`.
- **Codecs:** the stream FourCC must be one of H.264 (`avc1`, `h264`, `x264`) or HEVC (`hev1`, `hvc1`, `hevc`, `h265`); other codecs raise `UNSUPPORTED_MEDIA_TYPE`. `VideoConfig.allowed_codecs=None` disables this check (tests only). The frame pipeline ignores audio. Speech in the audio track is handled by a separate, optional step: [audio-transcription.md](audio-transcription.md).
- **Limits:** 500 MB (`FILE_TOO_LARGE`) and 600 s (`VIDEO_TOO_LONG`). Missing files raise `FILE_NOT_FOUND`; unopenable, undecodable or truncated streams raise `DECODE_FAILED`. `analyze_video_safe` returns these as the shared `ErrorResponse` envelope (the project's RFC 7807-style `code`/`message`/`retryable`/`httpStatus`).
- Decoding is OpenCV (`cv2.VideoCapture`); codec support therefore depends on the local OpenCV build.

## 2. Extracted Metadata
`probe_video` decodes the stream once to read every source timestamp and returns:
- `fps` (constant frame rate used for output timestamps) and `nominalFps` (container-reported), `frameCount` (output frames), `sourceFrameCount`, `durationSeconds`, `resolution` `[width, height]`, `codec`, `container`, `sizeBytes`.
- `timestamps`: whether source timestamps were usable, the maximum deviation from a uniform grid, `variableFrameRate`, and the policy applied.
- **Derived timestamps:** `timestamp = frameIndex / fps`; the source timestamp (relative to the first frame) is kept as `sourceTimestamp` when usable.
- **Variable frame rate:** a stream is VFR when any source timestamp deviates more than half a frame interval from a uniform grid at the nominal rate. VFR streams are normalized to a constant frame rate equal to the clip's average rate by **nearest-frame resampling** (frames may be repeated or skipped). No pixel interpolation is performed, so repeated frames carry the same measurements. If source timestamps are missing or not strictly increasing, the stream is treated as constant-rate at the nominal fps.

## 3. Identifiers and Lineage
- `videoId = "vid_" + sha256[:16]` of the file content. Frame IDs are `{videoId}_frame_{index:06d}`, where `index` is the position on the constant-rate grid, so they are stable across runs and sampling policies.
- The source file is only ever opened read-only (verified by a test). Per-frame artifacts are written under `<out-dir>/<videoId>/` (`frames/`, `masks/`, `cv/`, `frames.jsonl`, `job.json`, `summary.json`). Original-video storage in MinIO/S3 is **not** implemented; videos are read from the local path.
- Every result carries a `lineage` block (checksum, source path, codec, sampling) and each frame measurement its `frameId`, `sourceFrameIndex` and timestamps.

## 4. Sampling Policy
`VideoConfig.sample_every` (default 1, every frame) selects every N-th output frame; `max_frames` caps the count. CLI: `python -m cv.video_analysis <video> --sample-every N --max-frames M`.

## 5. Resumable processing
See [offline-operation.md](offline-operation.md#5-resumable-video-processing).

## Known limitations and failure modes
- `probe_video` decodes the whole stream once before analysis, which doubles decode time for long clips.
- The 10-minute limit is enforced on the output duration; very high-resolution videos are not additionally limited by memory.
- VFR handling depends on OpenCV reporting reliable per-frame timestamps; some containers report none.
- Camera jitter or dropped frames can still cause temporal misalignment that resampling cannot repair.

## Changelog
- **v1.1.0 (2026-10-14):** Implemented. Documented actual formats, limits, error codes, VFR policy (nearest-frame resampling instead of interpolation), IDs and sampling.
- **v1.0.0 (2026-10-12):** Initial specification draft.