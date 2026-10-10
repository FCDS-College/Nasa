"""Telemetry-banner OCR with per-field ROIs, validation and multi-frame voting.

Replaces the three divergent extractors that lived in notebooks/models.ipynb.
ROIs are fractions (x0, y0, x1, y1) of the frame and must be calibrated once
per video source; without ROIs the whole banner is parsed sequentially.
"""
from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np

FIELDS = ("fuel", "air", "fan", "rad")
ROI = Tuple[float, float, float, float]
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass
class OCRConfig:
    banner: ROI = (0.0, 0.0, 1.0, 0.25)
    rois: Optional[Dict[str, ROI]] = None
    # Plausible value ranges; readings outside are rejected as OCR noise.
    ranges: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "fuel": (0.0, 100.0), "air": (0.0, 1000.0),
        "fan": (-50.0, 500.0), "rad": (-50.0, 500.0)})
    frame_stride: int = 5
    max_samples: int = 40
    scale: float = 3.0
    min_votes: int = 2
    tesseract_cmd: Optional[str] = os.environ.get("TESSERACT_CMD")


def parse_numbers(text: str, max_len: int = 6) -> List[str]:
    return [n for n in _NUM.findall(text) if len(n) <= max_len]


def in_range(name: str, value: str, cfg: OCRConfig) -> bool:
    lo, hi = cfg.ranges[name]
    return lo <= float(value) <= hi


def preprocess(gray: np.ndarray, scale: float) -> np.ndarray:
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4)).apply(gray)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Tesseract expects dark text on a light background.
    return th if th.mean() > 127 else cv2.bitwise_not(th)


def _crop(frame: np.ndarray, roi: ROI) -> np.ndarray:
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = roi
    return frame[int(h * y0):int(h * y1), int(w * x0):int(w * x1)]


def read_frame(frame: np.ndarray, cfg: OCRConfig) -> Dict[str, Optional[str]]:
    import pytesseract
    if cfg.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = cfg.tesseract_cmd
    whitelist = "-c tessedit_char_whitelist=0123456789.-"
    out: Dict[str, Optional[str]] = {k: None for k in FIELDS}
    if cfg.rois:
        for name, roi in cfg.rois.items():
            gray = cv2.cvtColor(_crop(frame, roi), cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(preprocess(gray, cfg.scale),
                                               config=f"--psm 7 {whitelist}")
            nums = parse_numbers(text)
            if len(nums) == 1 and in_range(name, nums[0], cfg):
                out[name] = nums[0]
    else:
        gray = cv2.cvtColor(_crop(frame, cfg.banner), cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(preprocess(gray, cfg.scale), config="--psm 6")
        nums = parse_numbers(text)
        if len(nums) == len(FIELDS) and all(in_range(n, v, cfg) for n, v in zip(FIELDS, nums)):
            out = dict(zip(FIELDS, nums))
    return out


def vote(readings: Iterable[Dict[str, Optional[str]]], min_votes: int = 2) -> Dict[str, dict]:
    """Majority vote per field. confidence = winner share of non-empty reads."""
    readings = list(readings)
    result: Dict[str, dict] = {}
    for name in FIELDS:
        vals = [r[name] for r in readings if r.get(name) is not None]
        value, conf = None, 0.0
        if vals:
            top, n = Counter(vals).most_common(1)[0]
            if n >= min_votes:
                value, conf = top, n / len(vals)
        result[name] = {"value": value, "confidence": round(conf, 3), "votes": len(vals)}
    return result


def extract_from_video(video_path: str, cfg: Optional[OCRConfig] = None) -> Dict[str, dict]:
    cfg = cfg or OCRConfig()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(video_path)
    readings, idx = [], 0
    try:
        while len(readings) < cfg.max_samples:
            ok, frame = cap.read()  # sequential decode: seeking is far slower
            if not ok:
                break
            if idx % cfg.frame_stride == 0:
                readings.append(read_frame(frame, cfg))
            idx += 1
    finally:
        cap.release()
    return vote(readings, cfg.min_votes)


def field_accuracy(pred: Dict[str, dict], truth: Dict[str, str]) -> Dict[str, float]:
    """Exact-match per field against hand-labelled truth."""
    return {k: float(pred[k]["value"] == truth[k]) for k in truth if k in pred}
