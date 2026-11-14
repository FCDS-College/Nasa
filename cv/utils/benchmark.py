"""
benchmark.py - Measure what docs/cv/performance.md quotes: per-image latency and end-to-end video throughput of
the served CV pipeline, on this machine's CPU.

    python -m cv.utils.benchmark [--reps 10] [--video-frames 300] [--out cv/output/benchmark.json]

The pipeline is OpenCV/NumPy on the CPU. opencv-python-headless wheels have no CUDA path, so no GPU is used
(``gpuUsed`` is always false). Every image run is uncached and writes its mask and overlay artefacts, as the
API does.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import PIL
from PIL import Image

from cv.flame_cv import CVConfig, analyze_image
from cv.video_analysis import _overlay_mask, analyze_video
from cv.video_ingestion import VideoConfig, probe_video

SAMPLES = Path("datasets/samples/cv")
# One image per size and format found in the committed samples.
DEFAULT_IMAGES = [
    "FF-PSI-107/Downlink_Frame_Grabs_36f/vlcsnap-5790738.png",
    "FF-PSI-107/SPICE_GMT045_2009_jpegs/ISS018E030336.jpg",
    "FF-PSI-69/176F001D/176F001D_00660.png",
    "FF-PSI-69/C021H03C/C021H03C_00757.png",
    "FF-PSI-98/SAFFIRE_I_F2C2_jpeg/F2C2-1465938488551.jpeg",
    "FF-PSI-98/SAFFIRE_I_F2C2_Mapped_jpeg/Mapped_F2C2-1465938488551.jpeg",
    "FF-PSI-DSI/ACTIVITE04_HR1/DSI_SEQ2_ACTIVITE04_HR1_1018759522_1.png",
]
DEFAULT_VIDEO = "FF-PSI-25/videos/PSI-25_Raw Data_BASS_GMT50_SAMPLE_147_TEST_B1.mp4"


def environment() -> Dict[str, Any]:
    cpu = platform.processor() or ""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {"cpu": cpu, "cpuCount": os.cpu_count() or 1, "opencvThreads": cv2.getNumThreads(),
            "python": platform.python_version(), "opencv": cv2.__version__, "numpy": np.__version__,
            "pillow": PIL.__version__, "gpuUsed": False}


def _percentile(values: List[float], q: float) -> float:
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, int(round(q / 100 * (len(ordered) - 1)))))
    return ordered[k]


def bench_image(path: Any, work: Any, reps: int = 10, cfg: Optional[CVConfig] = None) -> Dict[str, Any]:
    """Uncached analyze_image latency in milliseconds (validation, preprocessing, segmentation, artefacts)."""
    work = Path(work)
    times = []
    for i in range(reps):
        start = time.perf_counter()
        analyze_image({"imagePath": str(path), "imageId": f"bench{i}"}, work / "cv", work / "masks", cfg=cfg)
        times.append((time.perf_counter() - start) * 1000)
    with Image.open(path) as im:
        size, mode = list(im.size), im.mode
    return {"image": Path(path).name, "size": size, "mode": mode, "reps": reps,
            "p50Ms": round(statistics.median(times), 1), "p95Ms": round(_percentile(times, 95), 1)}


def bench_video(path: Any, work: Any, max_frames: int = 300, allowed_codecs: Any = "default") -> Dict[str, Any]:
    """End-to-end analyze_video on every frame up to max_frames, with the probe and overlay-mask phases timed."""
    work = Path(work)
    kw = {} if allowed_codecs == "default" else {"allowed_codecs": allowed_codecs}
    vcfg = VideoConfig(sample_every=1, max_frames=max_frames, **kw)
    t0 = time.perf_counter()
    record = probe_video(path, vcfg)
    probe_s = time.perf_counter() - t0
    job = work / "mask_only"
    job.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    _overlay_mask(path, record, vcfg, job)
    mask_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    result = analyze_video(path, work / "run", video_cfg=vcfg, resume=False)
    total_s = time.perf_counter() - t0
    n = len(result["frameMeasurements"])
    per_frame_s = max(1e-9, total_s - probe_s - mask_s)
    return {"video": Path(path).name, "resolution": record["resolution"], "fps": record["fps"],
            "framesAnalysed": n, "probeS": round(probe_s, 3), "overlayMaskS": round(mask_s, 3),
            "totalS": round(total_s, 3), "framesPerSecond": round(n / per_frame_s, 1),
            "note": "framesPerSecond excludes the probe and overlay-mask passes, which run once per video"}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cv.utils.benchmark", description="CPU latency of the CV pipeline.")
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--video-frames", type=int, default=300)
    ap.add_argument("--out", default=None, help="Also write the results as JSON here.")
    args = ap.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="flame-bench-") as tmp:
        images = [bench_image(SAMPLES / p, Path(tmp) / f"img{i}", args.reps)
                  for i, p in enumerate(DEFAULT_IMAGES) if (SAMPLES / p).is_file()]
        video = SAMPLES / DEFAULT_VIDEO
        videos = [bench_video(video, Path(tmp) / "video", args.video_frames)] if video.is_file() else []
    report = {"environment": environment(), "images": images, "videos": videos}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
