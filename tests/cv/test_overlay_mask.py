"""tests/cv/test_overlay_mask.py - burned-in text overlays are excluded before flame segmentation (audit finding CV-1)."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from cv.overlay_mask import OverlayMaskConfig, build_overlay_mask
from cv.video_analysis import analyze_video
from cv.video_ingestion import VideoConfig

REPO = Path(__file__).resolve().parents[2]
SAMPLES = REPO / "datasets" / "samples" / "cv" / "FF-PSI-25" / "videos"
W, H = 320, 240


def _overlay(img: np.ndarray, value: int = 0) -> np.ndarray:
    """A telemetry-style banner: a fixed label row, a row with one changing value, and a date row."""
    cv2.putText(img, "FUEL  AIR  FAN  RAD", (20, 18), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), 1)
    cv2.putText(img, f"-2   0   41   {value}", (20, 34), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), 1)
    cv2.putText(img, "07/30/14 11:32", (20, 50), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), 1)
    return img


def _frames(n: int = 24, overlay: bool = True, flame=None) -> np.ndarray:
    """Grayscale stack; ``flame(i)`` returns (cx, cy, rx, ry) or None for frame i."""
    out = []
    for i in range(n):
        img = np.zeros((H, W, 3), np.uint8)
        if overlay:
            _overlay(img, value=i % 10)
        box = flame(i) if flame else None
        if box:
            cx, cy, rx, ry = box
            cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, (80, 200, 255), -1)
        out.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    return np.stack(out)


def test_overlay_text_rows_are_masked():
    mask, info = build_overlay_mask(_frames(), OverlayMaskConfig())
    banner = mask[4:56, 20:200]
    assert (banner > 0).mean() > 0.6, "the text rows should be covered"
    assert mask[120:, :].max() == 0, "nothing below the banner is masked"
    assert info["lines"] and info["pixelFraction"] > 0


def test_changing_digits_inside_a_row_are_covered():
    mask, _ = build_overlay_mask(_frames(), OverlayMaskConfig())
    # The last value on the second row changes every frame; it must still fall inside the row's mask.
    assert mask[24:36, 150:175].min() == 255


@pytest.mark.parametrize("flame", [
    lambda i: (160, 150, 60, 70),  # large steady flame present in every frame
    lambda i: (160, 150, 6, 6),    # small steady droplet flame present in every frame
])
def test_steady_flames_are_never_masked(flame):
    mask, info = build_overlay_mask(_frames(overlay=False, flame=flame), OverlayMaskConfig())
    assert mask.max() == 0 and info["lines"] == []


def test_flame_next_to_overlay_is_not_masked():
    mask, _ = build_overlay_mask(_frames(flame=lambda i: (160, 150, 40, 50)), OverlayMaskConfig())
    assert mask[110:190, 130:190].max() == 0


def test_disabled_returns_empty_mask():
    mask, info = build_overlay_mask(_frames(), OverlayMaskConfig(enabled=False))
    assert mask.max() == 0 and info["enabled"] is False


def _write_video(path: Path, n: int = 40) -> Path:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 20.0, (W, H))
    assert writer.isOpened()
    for i in range(n):
        img = _overlay(np.zeros((H, W, 3), np.uint8), value=i % 10)
        if 15 <= i < 30:  # the flame burns only in the middle of the clip
            cv2.ellipse(img, (160, 160), (30 + i % 3, 40), 0, 0, 360, (80, 200, 255), -1)
        writer.write(img)
    writer.release()
    return path


def test_video_detections_ignore_the_overlay(tmp_path):
    video = _write_video(tmp_path / "overlay.avi")
    result = analyze_video(video, tmp_path / "out", video_cfg=VideoConfig(allowed_codecs=None))
    present = [f for f in result["frameMeasurements"] if f["detectionStatus"] == "PRESENT"]
    assert present, "the real flame is still detected"
    assert all(f["boundingBox"]["ymin"] > 60 for f in present), "no detection lands on the overlay"
    assert all(15 <= f["frameIndex"] < 30 for f in present), "frames without a flame are not PRESENT"
    om = result["overlayMask"]
    assert om["enabled"] and om["lines"] and Path(om["uri"]).is_file() and om["checksum"].startswith("sha256:")


def test_disabling_the_mask_reproduces_the_old_failure(tmp_path):
    video = _write_video(tmp_path / "overlay.avi")
    cfg = VideoConfig(allowed_codecs=None, overlay=OverlayMaskConfig(enabled=False))
    result = analyze_video(video, tmp_path / "out", video_cfg=cfg)
    boxes = [f["boundingBox"] for f in result["frameMeasurements"] if f["detectionStatus"] == "PRESENT"]
    assert any(b["ymax"] <= 60 for b in boxes), "without the mask the overlay text is detected"
    assert result["overlayMask"]["enabled"] is False


# ------------------------------------------------- regression on committed NASA flight video (BASS-II)
def _sample(name: str) -> Path:
    path = next(SAMPLES.glob(f"*{name}*.mp4"), None)
    if path is None:
        pytest.skip(f"sample video {name} not installed")
    return path


@pytest.mark.parametrize("name", ["TEST_P12", "TEST_B1"])
def test_flight_video_overlay_is_never_a_flame(tmp_path, name):
    result = analyze_video(_sample(name), tmp_path, video_cfg=VideoConfig(sample_every=150))
    height = result["videoMetadata"]["resolution"][1]
    boxes = [f["boundingBox"] for f in result["frameMeasurements"] if f["detectionStatus"] == "PRESENT"]
    assert not [b for b in boxes if b["ymax"] <= 0.25 * height], "a telemetry-overlay box was reported as a flame"


def test_flight_video_real_flame_still_detected(tmp_path):
    # TEST_B1 burns between roughly frames 330 and 1095 (11-36 s); the overlay mask must not hide it.
    result = analyze_video(_sample("TEST_B1"), tmp_path, video_cfg=VideoConfig(sample_every=150))
    burning = [f for f in result["frameMeasurements"] if 450 <= f["frameIndex"] <= 900]
    assert burning and all(f["detectionStatus"] == "PRESENT" for f in burning)
