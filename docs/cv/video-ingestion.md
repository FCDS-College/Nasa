| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.2.0 | 2026-11-13 | A1, E3-6 | `cv/video_ingestion.py`, `cv/video_analysis.py`, `cv/overlay_mask.py` |

# Video Ingestion Specification (A1)

Implemented in `cv/video_ingestion.py` (`probe_video`, `iter_frames`) and driven by `cv/video_analysis.py`.

## 1. Scope and Accepted Formats
- **Containers:** `.mp4`, `.avi`, `.mov`. Anything else raises `UNSUPPORTED_MEDIA_TYPE`.
- **Codecs:** the stream FourCC must be one of H.264 (`avc1`, `h264`, `x264`) or HEVC (`hev1`, `hvc1`, `hevc`, `h265`); other codecs raise `UNSUPPORTED_MEDIA_TYPE`. `VideoConfig.allowed_codecs=None` disables this check (tests only). Audio is ignored: no audio extraction or transcription is performed.
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

## 5. Overlay exclusion (pipeline `cv-video-v1.1.0`)
Flight video carries burned-in text: the BASS-II telemetry banner (`FUEL AIR FAN RAD` values and a date line) sits in the top of every frame. White text on black is the brightest, highest-contrast region in the frame, so before v1.1.0 the segmenter reported it as a flame: on the committed sample `TEST_P12` every detection was the banner, and on the demo video `TEST_B1` 46 of 90 (audit finding CV-1, `.internal/research/2026-11-13-cv-audit.md`).

`cv/overlay_mask.py` builds one mask per video, before any frame is analyzed:
1. Sample `OverlayMaskConfig.sample_frames` (32) frames uniformly across the video.
2. A pixel is **persistent** when its 20th-percentile gray level is at least `max(60, Otsu)` and its 90th minus 20th percentile is at most 40: bright in almost every frame, and barely changing.
3. Persistent components of glyph size (at most 6% of the height and 10% of the width) are grouped at word spacing. A group of at least 3 glyphs that is at least twice as wide as tall is a **text row** (seed).
4. Glyphs are grouped again at banner spacing (20% of the width across, 3% of the height down). A group is masked as a padded rectangle only if it contains a seed, so short value fields (`-2`, `41`) and characters that change between frames are covered.

Each sampled frame is copied, the masked pixels are set to black (the segmenter's background), and the copy is analyzed. The source video is never modified. The mask is written to `<videoId>/overlay_mask.png`, and the result carries an `overlayMask` block (rows, pixel fraction, threshold, URI, checksum). The configuration is part of the job digest, so a checkpoint made under another mask configuration is discarded rather than mixed. `VideoConfig(overlay=OverlayMaskConfig(enabled=False))` restores the previous behaviour.

**Why only text.** A steady flame that burns for the whole clip is also persistent. A single flame, large or small, never forms a row of 3 or more glyphs, so it is not masked (tested with a large and a small steady flame). Large static scene content, such as cabin hardware or the bright glovebox floor in `TEST_T25_2ND_VIEW`, is deliberately **not** masked; that view is still reported as a flame (audit CV-1, open).

## 6. Resumable processing
See [offline-operation.md](offline-operation.md#5-resumable-video-processing).

## Known limitations and failure modes
- The overlay mask needs the banner to be visible in most of the sampled frames; an overlay shown for under ~80% of the clip is not detected. A small, glyph-sized flame within 3% of the frame height of a banner row would be merged into the banner and masked.
- A flame passing behind the masked banner is cut at the mask edge; the `occlusion` flag does not yet consider masked regions.
- `probe_video` decodes the whole stream once before analysis, and the overlay mask (§5) decodes it again to sample its frames, so a clip is decoded up to three times (the analysis pass decodes only up to the last sampled frame).
- The 10-minute limit is enforced on the output duration; very high-resolution videos are not additionally limited by memory.
- VFR handling depends on OpenCV reporting reliable per-frame timestamps; some containers report none.
- Camera jitter or dropped frames can still cause temporal misalignment that resampling cannot repair.

## Changelog
- **v1.2.0 (2026-11-13):** Overlay exclusion (§5): burned-in text rows are masked before segmentation; pipeline `cv-video-v1.1.0`.
- **v1.1.0 (2026-10-14):** Implemented. Documented actual formats, limits, error codes, VFR policy (nearest-frame resampling instead of interpolation), IDs and sampling.
- **v1.0.0 (2026-10-12):** Initial specification draft.