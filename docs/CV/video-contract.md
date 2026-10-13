| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess & Lead | Draft | 1.2.0 | 2026-10-12 | A4 | `cv/contracts/video_analysis_result.schema.json` |

# Video Analysis Result Contract (A4)

## 1. Overview
This document defines the official JSON Schema and contract for video analysis results processed by Workstream A. Every video ingestion pipeline execution must validate against `video_analysis_result.schema.json`.

## 2. Backward-Compatibility and Versioning
- Any breaking structural modification requires a major version increment in `schemaVersion`.
- Optional fields may be added under minor versions without disrupting existing API consumers.

## 3. Synthetic Example Payload
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
    "summaryUri": "C:/FCDS/Nasa/datasets/processed/videos/vid_sample_01_summary.json",
    "checksum": "sha256:abcdef1234567890"
  }
}
Known limitations and failure modes
Large video outputs can lead to heavy JSON payload sizes; frame-level arrays are recommended to be paginated or streamed for long clips.

Changelog
v1.2.0 (2026-10-12): Updated to align with auto-adaptive pipeline v1.2.0.

v1.0.0: Initial creation of video analysis result contract and schema.