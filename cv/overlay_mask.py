"""
overlay_mask.py - Find burned-in text overlays (telemetry banners, timestamps) in a video so that the
flame segmenter never measures them (CV audit finding CV-1).

Method: over frames sampled across the whole video, a pixel is *persistent* when it stays bright
(low percentile >= threshold) and barely changes (high minus low percentile <= max_variation). Text
overlays are persistent; a flame that is only on screen for part of the video is not.

Persistence alone is not enough: a steady flame that burns for the whole clip is persistent too. So
only persistent components that look like **text** are masked. These are glyph-sized components that
line up into a row of at least ``min_glyphs_per_line`` glyphs that is wider than it is tall. A lone
flame, large or small, is never a text row. Each detected row is masked as a padded rectangle,
which also covers the characters in that row that change from frame to frame.

Large static scene content (cabin hardware, a bright floor) is deliberately NOT masked here; see the
audit report (.internal/research/2026-11-13-cv-audit.md, CV-1/CV-2).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

OVERLAY_MASK_VERSION = "overlay-text-rows-v1"


@dataclass(frozen=True)
class OverlayMaskConfig:
    enabled: bool = True
    sample_frames: int = 32          # frames sampled uniformly across the video
    low_percentile: float = 20.0     # "bright in (almost) every frame"
    high_percentile: float = 90.0
    min_brightness: float = 60.0     # floor for the persistence threshold (gray levels)
    max_variation: float = 40.0      # high - low percentile, gray levels
    min_glyph_px: int = 3
    max_glyph_height_frac: float = 0.06
    max_glyph_width_frac: float = 0.10
    merge_width_frac: float = 0.03   # horizontal gap bridged between glyphs of one row
    merge_height_frac: float = 0.01  # vertical gap bridged between stacked banner rows
    line_merge_width_frac: float = 0.20  # column gap bridged between fields of a banner line
    line_merge_height_frac: float = 0.03  # row gap bridged inside a stacked banner block
    min_glyphs_per_line: int = 3
    min_line_aspect: float = 2.0     # row width / height
    pad_line_heights: float = 2.0    # horizontal padding, in row heights (covers changing end digits)
    pad_vertical_frac: float = 0.5   # vertical padding, in row heights


def _empty(shape: Tuple[int, int], cfg: OverlayMaskConfig, **extra: Any) -> Tuple[np.ndarray, Dict[str, Any]]:
    info = {"enabled": cfg.enabled, "method": OVERLAY_MASK_VERSION, "lines": [], "pixelFraction": 0.0,
            "threshold": None, "sampledFrames": 0, **extra}
    return np.zeros(shape, np.uint8), info


def _group(glyphs: np.ndarray, glyph_pixels: List[Tuple[int, int]], gap_x: float, gap_y: float):
    """Close glyphs with a (gap_x, gap_y) box; return labels, stats and glyph count per group."""
    # Odd kernel sizes keep the anchor centred, so closing only adds pixels (an even kernel shifts and
    # can drop the glyph pixels the lookup below relies on).
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, int(round(gap_x))) | 1, max(1, int(round(gap_y))) | 1))
    merged = cv2.morphologyEx(glyphs, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(merged, connectivity=8)
    per_group = np.zeros(count, int)
    for y, x in glyph_pixels:
        per_group[labels[y, x]] += 1
    return labels, stats, per_group


def build_overlay_mask(gray_frames: np.ndarray, cfg: OverlayMaskConfig) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Return a uint8 mask (255 = excluded) and a description, from a (N, H, W) uint8 grayscale stack."""
    if gray_frames.ndim != 3:
        raise ValueError("gray_frames must have shape (N, H, W).")
    n, h, w = gray_frames.shape
    if not cfg.enabled or n < 2:
        return _empty((h, w), cfg, sampledFrames=int(n))

    low = np.percentile(gray_frames, cfg.low_percentile, axis=0)
    high = np.percentile(gray_frames, cfg.high_percentile, axis=0)
    low_u8 = np.clip(low, 0, 255).astype(np.uint8)
    otsu, _ = cv2.threshold(low_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    threshold = max(cfg.min_brightness, float(otsu))
    persistent = ((low >= threshold) & ((high - low) <= cfg.max_variation)).astype(np.uint8)

    # Glyph-sized persistent components.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(persistent, connectivity=8)
    glyphs = np.zeros((h, w), np.uint8)
    glyph_pixels: List[Tuple[int, int]] = []  # one pixel ON each glyph (a centroid can fall off the stroke)
    for i in range(1, count):
        cw, ch, area = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT], stats[i, cv2.CC_STAT_AREA]
        if area >= cfg.min_glyph_px and ch <= cfg.max_glyph_height_frac * h and cw <= cfg.max_glyph_width_frac * w:
            ys, xs = np.nonzero(labels == i)
            glyphs[ys, xs] = 255
            glyph_pixels.append((int(ys[0]), int(xs[0])))

    # Seeds: glyphs joined at word spacing into rows; a row of >= min_glyphs_per_line glyphs that is wider
    # than tall is text. A lone flame, however steady, never forms one.
    seed_labels, seed_stats, seed_glyphs = _group(glyphs, glyph_pixels, cfg.merge_width_frac * w,
                                                  cfg.merge_height_frac * h)
    is_seed = (seed_glyphs >= cfg.min_glyphs_per_line) & (seed_stats[:, 2] >= cfg.min_line_aspect * seed_stats[:, 3])
    is_seed[0] = False

    # Lines: the same glyphs joined at column and row spacing (a banner is a stacked block). A line is kept
    # only if it contains a seed row, so short value fields ("-2", "41") are covered without masking
    # isolated blobs.
    line_labels, line_stats, line_glyphs = _group(glyphs, glyph_pixels, cfg.line_merge_width_frac * w,
                                                  cfg.line_merge_height_frac * h)
    seeded_lines = set(np.unique(line_labels[(np.isin(seed_labels, np.flatnonzero(is_seed)))]).tolist()) - {0}

    mask = np.zeros((h, w), np.uint8)
    lines: List[Dict[str, int]] = []
    for i in sorted(seeded_lines):
        x, y, rw, rh = (int(v) for v in line_stats[i, :4])
        row_h = max(1, min(rh, int(np.ceil(cfg.max_glyph_height_frac * h))))
        px, py = int(np.ceil(cfg.pad_line_heights * row_h)), int(np.ceil(cfg.pad_vertical_frac * row_h))
        x0, y0, x1, y1 = max(0, x - px), max(0, y - py), min(w, x + rw + px), min(h, y + rh + py)
        mask[y0:y1, x0:x1] = 255
        lines.append({"xmin": x0, "ymin": y0, "xmax": x1, "ymax": y1, "glyphs": int(line_glyphs[i])})

    lines.sort(key=lambda b: (b["ymin"], b["xmin"]))
    info = {"enabled": True, "method": OVERLAY_MASK_VERSION, "lines": lines,
            "pixelFraction": round(float((mask > 0).mean()), 6), "threshold": round(threshold, 2),
            "sampledFrames": int(n)}
    return mask, info


def apply_overlay_mask(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Return a copy of ``image`` with masked pixels set to black (the segmenter's background)."""
    if not mask.any():
        return image
    out = image.copy()
    out[mask > 0] = 0
    return out
