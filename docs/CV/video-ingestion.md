| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.0.0 | 2026-10-12 | A1 | `cv/video_ingestion.py` (planned) |

# Video Ingestion Specification (A1)

## 1. Scope and Accepted Formats
- **Accepted Formats:** MP4, AVI, MOV.
- **Codecs:** H.264 (AVC) and HEVC (H.265) video streams with AAC audio.
- **Limits:** Maximum file size of 500 MB and maximum duration of 10 minutes per video payload, ensuring reliable processing and preventing worker memory exhaustion.

## 2. Extracted Metadata
For every ingested video, the following metadata fields are programmatically extracted:
- **Frame Rate (fps):** Nominal and average frame rate.
- **Resolution:** Width and height in pixels.
- **Frame Count:** Total number of frames.
- **Timestamps:** Source timestamps vs. derived uniform frame intervals.
- **Variable Frame Rate (VFR) Handling:** VFR streams are normalized to a constant frame rate (CFR) via temporal interpolation during the ingestion phase to ensure consistent temporal metrics.

## 3. Identifiers and Lineage
- **Identifiers:** Every video receives a unique `videoId` derived from its SHA-256 content checksum. Frame IDs are stable, zero-padded, and derivable (format: `{videoId}_frame_{index:06d}`).
- **Immutability:** Original raw videos are stored immutably in object storage (MinIO/S3). Derived frames, bounding boxes, and masks maintain strict lineage back to their parent `videoId`.

## 4. Sampling Policies
- **Default Sampling:** Full-frame extraction for short clips, or uniform temporal subsampling (e.g., every $N$-th frame) configured via pipeline options for long-duration recordings.

## 5. Status and Error Codes
- Follows RFC 7807 error envelopes for ingestion failures (e.g., unsupported container format, corrupted headers, or timeout during stream decoding).

## Known limitations and failure modes
- High-frequency camera jitter or variable frame rate drops can introduce temporal misalignment if VFR normalization fails.
- Large video files require streaming chunk decoders to prevent RAM overflow.

## Changelog
- **v1.0.0 (2026-10-12):** Initial video ingestion specification draft for Phase 2 Workstream A.