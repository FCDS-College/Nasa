| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 2.0.0 | 2026-11-14 | A3, C1, CV audit CV-4 | `cv/flame_cv.py`, `cv/video_analysis.py`, `cv/utils/benchmark.py` |

# Performance Profile (v2.0.0)

The CV pipeline is **OpenCV and NumPy on the CPU**. It has no GPU path: `opencv-python-headless` wheels are built without CUDA, and the code does no batching. The numbers below were measured, not estimated.

## 1. How the numbers were measured

```bash
python -m cv.utils.benchmark --out cv/output/benchmark.json
```

- **Images:** each image is analysed 10 times, uncached, writing its mask and overlay artefacts as the API does; p50 and p95 latency are reported.
- **Video:** the BASS-II `TEST_B1` sample is analysed on every frame up to 300 (`sample_every = 1`), through the served path: probe, overlay mask, then per-frame analysis.
- **Machine:** Intel Xeon @ 2.10 GHz, 4 cores (OpenCV threads: 4), Python 3.13, OpenCV 4.14.0, NumPy 2.5.3, Pillow 13.0.0. Pipeline `cv-opencv-v1.4.0-auto` / `cv-video-v1.1.0`. Measured 2026-11-14, single run.

## 2. Image latency (per image, CPU)

| Sample | Size | Mode | p50 | p95 |
|---|---|---|---|---|
| FLEX 16-bit (`C021H03C_00757`) | 512 × 512 | I;16 | 63 ms | 65 ms |
| DSI (`…HR1_1018759522_1`) | 1024 × 1024 | L | 91 ms | 94 ms |
| SAFFIRE-I raw (`F2C2-1465938488551`) | 1280 × 920 | RGB | 104 ms | 135 ms |
| FLEX colour (`176F001D_00660`) | 640 × 480 | RGB | 106 ms | 107 ms |
| SPICE downlink (`vlcsnap-5790738`) | 640 × 480 | RGB | 120 ms | 163 ms |
| SAFFIRE-I mapped | 1705 × 1222 | RGB | 124 ms | 127 ms |
| SPICE ISS photo (`ISS018E030336`) | 3008 × 2000 | RGB | 170 ms | 193 ms |

Every image is letterboxed to at most 512 px before segmentation, so latency grows slowly with input size (63 ms at 512² to 170 ms at 3008 × 2000).

## 3. Video throughput (CPU)

| Phase | Measured on `TEST_B1` (720 × 480, 29.97 fps) |
|---|---|
| Probe (decode every frame's timestamp, checksum) | 0.34 s, once per video |
| Overlay mask (`cv/overlay_mask.py`, 32 sampled frames) | 0.49 s, once per video |
| Per-frame analysis | **33.6 frames per second** (300 frames) |

A 60 s clip at `sample_every = 1` (about 1,800 frames) therefore takes about 55 s on this machine. At the API default (`sample_every = 30`, at most 300 frames), it takes about 2 s plus the two once-per-video passes.

## Known limitations

- **No GPU acceleration:** a GPU in the machine does not change these numbers. An earlier version of this page reported NVIDIA L40S VRAM use, a 3.5× GPU speed-up, batch sizes and vLLM co-existence limits; none of that has code behind it, and it is removed (CV audit, CV-4).
- **Single-run numbers:** they will differ between runs and machines. Re-run the command above on the target machine before sizing a deployment.
- **Artefact writes are disk I/O:** each frame writes a PNG frame, mask and overlay. On slow disks this, not computation, limits video throughput.
- **One process per job:** one video job is processed sequentially in one worker; run more RQ workers to process several jobs in parallel.

## Changelog

- **v2.0.0 (2026-11-14):** Replaced unmeasured GPU claims with CPU measurements from `cv/utils/benchmark.py` (images and video, command and machine stated).
- **v1.2.0 (2026-10-12):** Initial performance and GPU profile (unmeasured; withdrawn).
