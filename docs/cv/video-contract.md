| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess & Lead | Draft | 1.4.0 | 2026-11-13 | A4 | `cv/contracts/video_analysis_result.schema.json`, `cv/video_analysis.py` |

# Video Analysis Result Contract (A4)

## 1. Overview
This document defines the JSON Schema and contract for video analysis results. `cv/video_analysis.py` (`analyze_video`) produces payloads that must validate against `cv/contracts/video_analysis_result.schema.json`; `tests/cv/test_video_pipeline.py` and `tests/cv/test_contract_examples.py` enforce this.

API exposure (contract 0.3.0): `POST /api/analyses` with a `video` part creates a `flame_video` analysis. The worker maps this payload to the snake_case `FlameVideoAnalysisResult` in `docs/api/openapi.json` (`apps/api/flame_api/worker.py`, `_adapt_video_result`); this camelCase schema remains the pipeline's internal contract.

## 2. Backward-Compatibility and Versioning
- Any breaking structural modification requires a major version increment in `schemaVersion`.
- Optional fields may be added under minor versions without disrupting existing API consumers. v1.3.0 and v1.4.0 only add optional fields, so v1.2.0 payloads (the example below) remain valid.
- The schema does not restrict `schemaVersion` to a constant; consumers should read it and ignore unknown optional fields.

## 3. Fields
| Field | Notes |
|---|---|
| `videoId` | `vid_` + first 16 hex characters of the source SHA-256. |
| `videoMetadata` | `fps` (constant frame rate used for timestamps), `frameCount`, `durationSeconds`, `resolution` `[width, height]`. |
| `lineage` (v1.3.0) | Source checksum, container, codec, source frame count, timestamp/VFR handling and sampling policy. |
| `overlayMask` (v1.4.0) | Burned-in text excluded before segmentation: `enabled`, `method`, `lines[]` (`xmin`, `ymin`, `xmax`, `ymax` in original pixels, `glyphs`), `pixelFraction`, `threshold`, `sampledFrames`, and the mask image `uri` and `checksum`. See [video-ingestion.md §5](video-ingestion.md#5-overlay-exclusion-pipeline-cv-video-v110). |
| `frameMeasurements[]` | `frameIndex`, `timestamp` (= `frameIndex / fps`), `detectionStatus`, `pixelArea` (null when not present). Optional: `frameId` (`{videoId}_frame_{index:06d}`), `sourceFrameIndex`, `sourceTimestamp`, `centroid`, `boundingBox`, `qualityFlags`, `detectionConfidence`, `error` (a frame whose analysis failed is reported as `UNCERTAIN` with the error code). |
| `temporalSummary` | `persistenceRate`, `flickerFrequencyHz` (number, or the string `"not estimable"`). Optional: `flickerStatus`, `flickerNote` (reason), `persistenceWindow`, `areaChangeRate`, `trackingStability`, `trackSessions`, `aggregationConfig`. |
| `artifacts` | Repo-relative `summaryUri` and its `checksum`. |

Flicker validity conditions are specified in [temporal-analysis.md](temporal-analysis.md).

## 4. Synthetic Example Payload (v1.2.0)
```json
{
  "schemaVersion": "1.2.0",
  "status": "SUCCESS",
  "analysisId": "vid_an_987654321",
  "videoId": "vid_sample_01",
  "pipelineVersion": "cv-opencv-v1.2.0-auto",
  "videoMetadata": {
    "fps": 30.0,
    "frameCount": 90,
    "durationSeconds": 3.0,
    "resolution": [1920, 1080]
  },
  "frameMeasurements": [
    {
      "frameIndex": 0,
      "timestamp": 0.0,
      "detectionStatus": "PRESENT",
      "pixelArea": 45000.5
    }
  ],
  "temporalSummary": {
    "persistenceRate": 1.0,
    "flickerFrequencyHz": "not estimable"
  },
  "artifacts": {
    "summaryUri": "datasets/processed/videos/vid_sample_01_summary.json",
    "checksum": "sha256:abcdef1234567890"
  }
}
```

## Known limitations and failure modes
- Large video outputs can lead to heavy JSON payload sizes; frame-level arrays are recommended to be paginated or streamed for long clips.
- Error responses use the shared `ErrorResponse` envelope (`status: "ERROR"`), which is not described by this schema.

## Changelog
- **v1.4.0 (2026-11-13):** Added the optional `overlayMask` block (pipeline `cv-video-v1.1.0`).
- **v1.3.0 (2026-10-14):** Added optional lineage, frame ID, centroid, bounding box, quality flags and extended temporal summary fields; documented the fields; closed the example's code fence and replaced its absolute path.
- **v1.2.0 (2026-10-12):** Updated to align with auto-adaptive pipeline v1.2.0.
- **v1.0.0:** Initial creation of video analysis result contract and schema.