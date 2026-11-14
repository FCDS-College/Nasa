"""tests/cv/test_benchmark.py - the CV benchmark runs and reports what docs/cv/performance.md quotes."""
from __future__ import annotations

import cv2
import numpy as np

from cv.flame_cv import make_synthetic_flame
from cv.utils import benchmark


def test_image_benchmark_reports_percentiles(tmp_path):
    img = tmp_path / "flame.png"
    make_synthetic_flame(img, size=(640, 480), blobs=[(320, 240, 60, 60)])
    row = benchmark.bench_image(img, tmp_path / "work", reps=3)
    assert row["size"] == [640, 480] and row["reps"] == 3
    assert 0 < row["p50Ms"] <= row["p95Ms"]


def test_video_benchmark_reports_phases(tmp_path):
    video = tmp_path / "clip.avi"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 20.0, (320, 240))
    for i in range(12):
        frame = np.zeros((240, 320, 3), np.uint8)
        cv2.ellipse(frame, (160, 120), (30 + i % 3, 40), 0, 0, 360, (80, 200, 255), -1)
        writer.write(frame)
    writer.release()
    row = benchmark.bench_video(video, tmp_path / "work", max_frames=10, allowed_codecs=None)
    assert row["framesAnalysed"] == 10
    # A 12-frame clip probes in a few milliseconds, so only the ordering is checked, not a minimum.
    assert row["probeS"] >= 0 and row["overlayMaskS"] >= 0 and row["totalS"] >= row["probeS"]
    assert row["framesPerSecond"] > 0


def test_environment_is_recorded():
    env = benchmark.environment()
    assert env["cpuCount"] >= 1 and env["opencv"] and env["gpuUsed"] is False
