"""Flame-spread rate of SAFFIRE-I sample 1 from the distortion-corrected ("Mapped") camera frames of PSI-98.

Method (see physics/README.md for the numbers):
  * Each frame is decoded at quarter resolution ("qpx" below) and reduced to column profiles of the green channel (mean over
    rows) and the red channel (99th percentile over rows).
  * About a fifth of the frames are LED-lit and show the burned region (dark) against unburned fabric (bright). In those frames the
    burn boundary is the last column above the mid level between the 5th and 95th percentile of the green profile.
  * The boundary moves in a straight line in both cameras. Camera 2 sees the same front shifted by a constant number of columns
    (estimated in the overlap window), so the two tracks chain into one.
  * A straight-line fit over the steady window gives px/s, converted to mm/s with the checkerboard scale (see MM_PER_QPX).
Needs pillow and numpy. The Mapped zips come from knowledge/ingestion/psi_download.py with
datasets/manifests/saffire1_s1_mapped_selection.csv.
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import re
import zipfile
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "datasets" / "raw" / "psi_api" / "PSI-98" / "Raw Data"
DEFAULT_OUT = REPO / "physics" / "results" / "saffire1_s1_flame_front.csv"

LIT_GREEN = 30.0  # mean green level above which a frame counts as LED-lit
DARK_GREEN = 8.0  # ... and below which it counts as unlit (flame glow only)
MOVING_COLUMNS = {"S1C1": (65, 365), "S1C2": (125, 400)}  # columns where the lit edge is on the sample, not on the card margin
OVERLAP_S = (170.0, 270.0)  # both cameras see the moving front here
HANDOVER_S = 270.0  # camera 1 up to here, camera 2 after
STEADY_S = (100.0, 410.0)  # steady-spread window (the first ~40 s are a faster ignition transient)
# Physical scale, mm per quarter-resolution pixel, from the PSI-98 "30mmBlock" checkerboard images, Mapped (distortion-corrected)
# version: the blocks are 66.7 px for 30 mm in both cameras (Fourier peak, left/right/centre crops agree within about 1.5 %), i.e.
# 0.450 mm per full-resolution pixel. This assumes the checkerboard lay in the sample plane. It agrees with the bright-band width
# of a lit burn frame (899 px for 0.40 m gives 0.445 mm per px) and not with taking 940 mm as the front travel (0.49 mm per px).
MM_PER_QPX = 1.80


@dataclass(frozen=True)
class Profiles:
    epoch_ms: np.ndarray  # (n,) int64
    mean_green: np.ndarray  # (n,) mean green level of the whole frame
    green_cols: np.ndarray  # (n, W) mean green per column
    red_p99_cols: np.ndarray  # (n, W) 99th percentile of red per column

    @property
    def t(self) -> np.ndarray:
        return (self.epoch_ms - self.epoch_ms[0]) / 1000.0


def _process_zip(zip_path: str):
    from PIL import Image  # imported here so the pure functions below work without pillow

    out = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            m = re.search(r"-(\d{13})\.jpe?g$", info.filename, re.I)
            if not m:
                continue
            img = Image.open(io.BytesIO(zf.read(info.filename)))
            img.draft("RGB", (img.width // 4, img.height // 4))
            a = np.asarray(img.convert("RGB"), dtype=np.float32)
            out.append((int(m.group(1)), float(a[..., 1].mean()), a[..., 1].mean(0), np.percentile(a[..., 0], 99, axis=0)))
    return out


def extract_profiles(camera: str, raw_dir: Path = RAW_DIR, workers: int = 6) -> Profiles:
    """Column profiles for every frame of one camera (e.g. 'S1C1'). Frames repeated across zips (S1C2 part3 repeats part2) are kept once."""
    zips = sorted(glob.glob(str(raw_dir / f"*{camera}_JPEG_Mapped*.zip")))
    if not zips:
        raise FileNotFoundError(f"no Mapped zips for {camera} in {raw_dir}; download datasets/manifests/saffire1_s1_mapped_selection.csv")
    with Pool(min(workers, len(zips))) as pool:
        parts = pool.map(_process_zip, zips)
    seen, rows = set(), []
    for part in parts:
        for row in part:
            if row[0] not in seen:
                seen.add(row[0])
                rows.append(row)
    rows.sort(key=lambda r: r[0])
    return Profiles(
        epoch_ms=np.array([r[0] for r in rows], dtype=np.int64),
        mean_green=np.array([r[1] for r in rows], dtype=np.float32),
        green_cols=np.stack([r[2] for r in rows]),
        red_p99_cols=np.stack([r[3] for r in rows]),
    )


def load_profiles(camera: str, cache_dir: Path | None, raw_dir: Path = RAW_DIR) -> Profiles:
    cache = cache_dir / f"saffire_profiles_{camera}.npz" if cache_dir else None
    if cache is not None and cache.exists():
        z = np.load(cache)
        return Profiles(z["epoch_ms"], z["mean_green"], z["green_cols"], z["red_p99_cols"])
    prof = extract_profiles(camera, raw_dir)
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, epoch_ms=prof.epoch_ms, mean_green=prof.mean_green, green_cols=prof.green_cols,
                            red_p99_cols=prof.red_p99_cols)
    return prof


def lit_edges(prof: Profiles, lit_green: float = LIT_GREEN) -> tuple[np.ndarray, np.ndarray]:
    """(times, columns) of the last column above the mid level, one per lit frame."""
    lit = prof.mean_green > lit_green
    p = prof.green_cols[lit]
    hi, lo = np.percentile(p, 95, axis=1), np.percentile(p, 5, axis=1)
    above = p > (lo + 0.5 * (hi - lo))[:, None]
    edge = p.shape[1] - 1 - np.argmax(above[:, ::-1], axis=1)
    return prof.t[lit], edge.astype(float)


def glow_centroid(prof: Profiles) -> tuple[np.ndarray, np.ndarray]:
    """(times, columns) of the red glow centre in unlit frames (a second, independent view of the front)."""
    weight = np.clip(prof.red_p99_cols - 3.2, 0, None)  # 3.2 is the red background level of the dark frames
    weight = np.where(weight > 12, weight, 0.0)
    total = weight.sum(1)
    keep = (prof.mean_green < DARK_GREEN) & (total > 200)
    centre = (weight * np.arange(weight.shape[1])).sum(1) / np.where(total > 0, total, 1)
    return prof.t[keep], centre[keep]


def moving_part(t: np.ndarray, edge: np.ndarray, lo: float, hi: float) -> tuple[np.ndarray, np.ndarray]:
    keep = (edge > lo) & (edge < hi)
    return t[keep], edge[keep]


def fit_line(t: np.ndarray, y: np.ndarray, lo: float, hi: float) -> tuple[float, float, int]:
    """Slope, residual standard deviation and point count of a straight line over t in [lo, hi]."""
    k = (t >= lo) & (t <= hi)
    p = np.polyfit(t[k], y[k], 1)
    return float(p[0]), float((y[k] - np.polyval(p, t[k])).std()), int(k.sum())


def camera_offset(t1, e1, t2, e2, window=OVERLAP_S) -> tuple[float, float]:
    """Mean and standard deviation of (camera 2 column - camera 1 column) for the same front, over the overlap window."""
    ov = np.arange(window[0], window[1], 1.0)
    d = np.interp(ov, t2, e2) - np.interp(ov, t1, e1)
    return float(d.mean()), float(d.std())


def combine(t1, e1, t2, e2, offset: float, handover: float = HANDOVER_S) -> tuple[np.ndarray, np.ndarray]:
    """One front track in camera-1 columns: camera 1 up to the handover time, camera 2 (shifted back by the offset) after."""
    t = np.r_[t1[t1 <= handover], t2[t2 > handover]]
    e = np.r_[e1[t1 <= handover], e2[t2 > handover] - offset]
    order = np.argsort(t)
    return t[order], e[order]


def run(cache_dir: Path | None, out: Path, raw_dir: Path = RAW_DIR) -> dict:
    p1, p2 = load_profiles("S1C1", cache_dir, raw_dir), load_profiles("S1C2", cache_dir, raw_dir)
    t1_all, e1_all = lit_edges(p1)
    t2_all, e2_all = lit_edges(p2)
    t1, e1 = moving_part(t1_all, e1_all, *MOVING_COLUMNS["S1C1"])
    t2, e2 = moving_part(t2_all, e2_all, *MOVING_COLUMNS["S1C2"])
    off, off_sd = camera_offset(t1, e1, t2, e2)
    tc, ec = combine(t1, e1, t2, e2, off)
    slope, resid, n = fit_line(tc, ec, *STEADY_S)
    result = {
        "camera_offset_cols": off, "camera_offset_sd": off_sd,
        "slope_c1_px_s": -fit_line(t1, e1, t1.min(), t1.max())[0], "slope_c2_px_s": -fit_line(t2, e2, t2.min(), t2.max())[0],
        "steady_px_s": -slope, "steady_resid_px": resid, "steady_points": n, "t_start_s": float(tc.min()), "t_end_s": float(tc.max()),
        "steady_mm_s": -slope * MM_PER_QPX,
        "window_slopes_px_s": {a: -fit_line(tc, ec, a, a + 40)[0] for a in range(10, 410, 40) if ((tc >= a) & (tc < a + 40)).sum() > 50},
    }
    gt1, gc1 = glow_centroid(p1)
    k = (gt1 > 60) & (gt1 < 260)
    result["glow_slope_c1_px_s"] = -fit_line(gt1[k], gc1[k], 60, 260)[0]
    origin = float(np.median(e1_all[t1_all < 8.0]))  # the lit edge sits on the card margin before the front starts to move
    rows = []
    for sec in range(int(tc.min()) + 1, int(tc.max())):
        k = (tc >= sec - 0.5) & (tc < sec + 0.5)
        if k.sum() >= 3:  # LED flashes are intermittent, so some seconds have too few lit frames
            rows.append((sec, float(np.median(ec[k]))))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["t_s", "front_col_qpx", "x_mm"])
        for s, c in rows:
            w.writerow([s, round(c, 1), round((origin - c) * MM_PER_QPX, 1)])
    result["origin_col"] = origin
    result["rows_written"] = len(rows)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    ap.add_argument("--cache-dir", type=Path, help="keep the per-frame profiles here so a rerun skips the 3-4 minute decode")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    for key, value in run(args.cache_dir, args.out, args.raw_dir).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
