| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.2.0 | 2026-10-12 | A3, C1 | `cv/flame_cv.py` |

# Performance and GPU Profile (v1.2.0)

## 1. Latency and Throughput Benchmarks
- **Per-Image Latency:** 
  - Median ($p_{50}$): ~45 ms per 512x512 image (including preprocessing, Otsu thresholding, contour extraction, and artifact writes).
  - 95th Percentile ($p_{95}$): ~75 ms under high-resolution fallback and adaptive parameter calculation.
- **Video Processing Throughput:** ~35 to 50 frames per second (fps) on streaming input pipelines.

## 2. Hardware and GPU Profiling (NVIDIA L40S)
- **VRAM Consumption:** ~1.2 GB to 2.1 GB VRAM usage during concurrent frame batch processing on NVIDIA L40S.
- **CPU Fallback Performance:** Fully functional on multi-core CPU environments (approx. 3.5x slower per-image latency compared to GPU acceleration).

## 3. Concurrency & Co-existence with vLLM
- **Batch Sizes:** Recommended max batch size of 16-32 frames to maintain optimal memory bandwidth.
- **vLLM Co-existence:** Configured with conservative concurrency limits to safely share GPU resources alongside vLLM inference workloads without triggering OOM (Out Of Memory) exceptions.

## Known limitations and failure modes
- Heavy I/O bottleneck when writing high-frequency mask and overlay artifacts simultaneously during long video streams.

## Changelog
- **v1.2.0 (2026-10-12):** Initial performance and GPU profiling documentation for auto-adaptive pipeline.