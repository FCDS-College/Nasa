"""
temporal_analysis.py - Tracking and temporal metrics over per-frame flame measurements (A2 / E3-7).

Input is a list of frame measurement dicts (see ``video_analysis``) with at least ``frameIndex``,
``timestamp`` and ``detectionStatus``; optional ``pixelArea``, ``centroid`` ({x, y}),
``boundingBox`` ({xmin, ymin, xmax, ymax}) and ``qualityFlags``. Frames must be in time order.
Flicker frequency is only reported when its validity conditions hold; otherwise it is the string
``"not estimable"`` together with a reason.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import numpy as np

NOT_ESTIMABLE = "not estimable"


@dataclass(frozen=True)
class TemporalConfig:
    max_gap_s: float = 0.5
    min_iou: float = 0.1
    window_s: float = 1.0
    max_expected_flicker_hz: float = 10.0
    min_flicker_duration_s: float = 2.0
    min_flicker_samples: int = 32
    min_flicker_hz: float = 0.5
    min_peak_ratio: float = 15.0
    excluded_flags: tuple = ("blur", "saturationClipping")


def _iou(a: Dict[str, float], b: Dict[str, float]) -> float:
    ix = max(0.0, min(a["xmax"], b["xmax"]) - max(a["xmin"], b["xmin"]))
    iy = max(0.0, min(a["ymax"], b["ymax"]) - max(a["ymin"], b["ymin"]))
    inter = ix * iy
    union = ((a["xmax"] - a["xmin"]) * (a["ymax"] - a["ymin"]) +
             (b["xmax"] - b["xmin"]) * (b["ymax"] - b["ymin"]) - inter)
    return inter / union if union > 0 else 0.0


def _present(f: Dict[str, Any]) -> bool:
    return f.get("detectionStatus") == "PRESENT"


def assign_tracks(frames: List[Dict[str, Any]], cfg: TemporalConfig) -> List[Optional[int]]:
    """Return a track/session ID per frame (None when not PRESENT).

    A new session starts after a gap longer than ``max_gap_s`` or when the bounding box no
    longer overlaps the previous one by at least ``min_iou``.
    """
    ids: List[Optional[int]] = []
    session = 0
    last_box: Optional[Dict[str, float]] = None
    last_t: Optional[float] = None
    for f in frames:
        if not _present(f):
            ids.append(None)
            continue
        box = f.get("boundingBox")
        if last_t is None:
            session = 1
        else:
            gap = f["timestamp"] - last_t > cfg.max_gap_s
            moved = bool(box and last_box and _iou(box, last_box) < cfg.min_iou)
            if gap or moved:
                session += 1
        ids.append(session)
        last_box, last_t = box, f["timestamp"]
    return ids


def area_change_rates(frames: List[Dict[str, Any]]) -> List[Optional[float]]:
    """(A_t - A_{t-1}) / dt between consecutive frames that both have an area; else None."""
    rates: List[Optional[float]] = [None]
    for prev, cur in zip(frames, frames[1:]):
        a0, a1 = prev.get("pixelArea"), cur.get("pixelArea")
        dt = cur["timestamp"] - prev["timestamp"]
        rates.append((a1 - a0) / dt if a0 is not None and a1 is not None and dt > 0 else None)
    return rates


def _window_len(frames: List[Dict[str, Any]], window_s: float) -> int:
    if len(frames) < 2:
        return 1
    dt = (frames[-1]["timestamp"] - frames[0]["timestamp"]) / (len(frames) - 1)
    return max(2, int(round(window_s / dt))) if dt > 0 else 2


def persistence(frames: List[Dict[str, Any]], cfg: TemporalConfig) -> Dict[str, Any]:
    """Overall PRESENT fraction plus the sliding-window mean/minimum."""
    if not frames:
        return {"rate": 0.0, "windowMean": None, "windowMin": None, "windowFrames": 0}
    flags = np.array([_present(f) for f in frames], dtype=float)
    w = min(_window_len(frames, cfg.window_s), len(frames))
    kernel = np.ones(w) / w
    windows = np.convolve(flags, kernel, mode="valid")
    return {"rate": float(flags.mean()), "windowMean": float(windows.mean()), "windowMin": float(windows.min()),
            "windowFrames": int(w)}


def tracking_stability(frames: List[Dict[str, Any]], cfg: TemporalConfig) -> Optional[float]:
    """Mean rolling variance (px^2) of the centroid; None when too few centroids exist."""
    pts = [(f["centroid"]["x"], f["centroid"]["y"]) if _present(f) and f.get("centroid") else None for f in frames]
    w = _window_len(frames, cfg.window_s)
    values = []
    for i in range(0, max(1, len(pts) - w + 1)):
        chunk = [p for p in pts[i:i + w] if p is not None]
        if len(chunk) >= 2:
            arr = np.asarray(chunk)
            values.append(float(arr[:, 0].var() + arr[:, 1].var()))
    return float(np.mean(values)) if values else None


def _longest_valid_run(frames: List[Dict[str, Any]], cfg: TemporalConfig) -> List[Dict[str, Any]]:
    """Longest run of consecutive (uniformly sampled) frames that are PRESENT and of usable quality."""
    best: List[Dict[str, Any]] = []
    run: List[Dict[str, Any]] = []
    for f in frames:
        flags = f.get("qualityFlags") or {}
        ok = (_present(f) and f.get("pixelArea") is not None
              and not any(flags.get(name) for name in cfg.excluded_flags))
        if ok:
            run.append(f)
            if len(run) > len(best):
                best = list(run)
        else:
            run = []
    return best


def flicker_frequency(frames: List[Dict[str, Any]], fps: float, sample_every: int,
                      cfg: TemporalConfig) -> Dict[str, Any]:
    """Dominant frequency of the pixel-area signal, or "not estimable" with a reason."""
    def no(reason: str) -> Dict[str, Any]:
        return {"valueHz": NOT_ESTIMABLE, "reason": reason}

    fs = fps / sample_every
    if fs < 2 * cfg.max_expected_flicker_hz:
        return no(f"sampling rate {fs:.2f} Hz is below the Nyquist rate for {cfg.max_expected_flicker_hz:g} Hz")
    run = _longest_valid_run(frames, cfg)
    if len(run) < cfg.min_flicker_samples:
        return no(f"longest valid run has {len(run)} samples; need {cfg.min_flicker_samples}")
    duration = run[-1]["timestamp"] - run[0]["timestamp"]
    if duration < cfg.min_flicker_duration_s:
        return no(f"longest valid run spans {duration:.2f}s; need {cfg.min_flicker_duration_s:g}s")

    signal = np.array([f["pixelArea"] for f in run], dtype=np.float64)
    t = np.arange(len(signal))
    signal = signal - np.polyval(np.polyfit(t, signal, 1), t)
    if float(np.std(signal)) < 1e-9:
        return no("area signal is constant")
    spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal)))) ** 2
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / fs)
    band = (freqs >= cfg.min_flicker_hz) & (freqs <= cfg.max_expected_flicker_hz)
    if not band.any():
        return no("no spectral bins inside the expected flicker band")
    band_power = spectrum[band]
    peak = int(np.argmax(band_power))
    noise = float(np.median(band_power))
    ratio = float(band_power[peak] / noise) if noise > 0 else float("inf")
    if ratio < cfg.min_peak_ratio:
        return no(f"no dominant spectral peak (peak/median power {ratio:.1f} < {cfg.min_peak_ratio:g})")
    return {"valueHz": round(float(freqs[band][peak]), 4), "reason": None, "peakToMedianPower": round(ratio, 2),
            "samples": len(run), "windowSeconds": round(duration, 4)}


def summarize(frames: List[Dict[str, Any]], fps: float, sample_every: int,
              cfg: Optional[TemporalConfig] = None) -> Dict[str, Any]:
    """Compute the temporal summary block for a video result."""
    cfg = cfg or TemporalConfig()
    track_ids = assign_tracks(frames, cfg)
    rates = [r for r in area_change_rates(frames) if r is not None]
    pers = persistence(frames, cfg)
    flicker = flicker_frequency(frames, fps, sample_every, cfg)
    return {
        "persistenceRate": round(pers["rate"], 6),
        "flickerFrequencyHz": flicker["valueHz"],
        "flickerStatus": "ESTIMATED" if flicker["reason"] is None else "NOT_ESTIMABLE",
        "flickerNote": flicker["reason"],
        "persistenceWindow": {"frames": pers["windowFrames"], "mean": pers["windowMean"], "min": pers["windowMin"]},
        "areaChangeRate": {
            "unit": "pixels^2 per second",
            "meanAbs": float(np.mean(np.abs(rates))) if rates else None,
            "maxAbs": float(np.max(np.abs(rates))) if rates else None,
            "pairs": len(rates),
        },
        "trackingStability": {"unit": "pixels^2 (mean rolling centroid variance)",
                              "value": tracking_stability(frames, cfg)},
        "trackSessions": len({i for i in track_ids if i is not None}),
        "aggregationConfig": asdict(cfg) | {"fps": fps, "sampleEvery": sample_every},
    }
