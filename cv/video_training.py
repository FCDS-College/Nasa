"""Train and evaluate video-level models on the PSI-25 (BASS-II) videos.

Labels come from the PSI-25 experimental table (initial O2 %, fuel family).
Evaluation is leave-one-test-out (views of the same test share a group), and
every model is compared against a trivial baseline. Results are written to
contracts/training_report.json so accuracy is tracked across iterations.

    python -m cv.video_training --videos datasets/raw/psi_api/PSI-25/Raw\\ Data
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

from cv.video_embedding import extract_embeddings, get_device

BANNER_ROWS = 0.2  # top rows hold the telemetry/date overlay; masked to avoid leaking test identity

FUEL_FAMILY = [
    ("nomex", "nomex"), ("candle", "wax"), ("wax", "wax"), ("sibal", "sibal"),
    ("rod", "rod"), ("spherical", "sphere"), ("pmma", "pmma"), ("film", "pmma"),
]


def fuel_family(material: str) -> str:
    m = material.lower()
    for key, fam in FUEL_FAMILY:
        if key in m:
            return fam
    return "other"


def video_test_id(path: str) -> str:
    return re.search(r"TEST_([A-Z]+\d+)", Path(path).name).group(1)


def load_labels(table_csv: str) -> Dict[str, dict]:
    import pandas as pd
    df = pd.read_csv(table_csv)
    df.columns = [re.sub(r"\s+", " ", c).strip() for c in df.columns]
    out = {}
    for _, r in df.iterrows():
        o2 = pd.to_numeric(r.get("Calibrated initial O2 % by vol"), errors="coerce")
        out[str(r["Test #"]).strip()] = {
            "o2": None if pd.isna(o2) else float(o2),
            "fuel": fuel_family(str(r["Fuel Sample Material"])),
            "flow_restrictor": str(r["Flow restrictor"]).strip(),
        }
    return out


def sample_frames(path: str, n: int = 64) -> List[np.ndarray]:
    """Uniformly spaced RGB frames, read sequentially (grab() skips decoding)."""
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    want = set(np.linspace(0, max(total - 2, 0), n).astype(int).tolist())
    frames, i = [], 0
    while i <= max(want):
        if i in want:
            ok, f = cap.read()
            if not ok:
                break
            f[: int(f.shape[0] * BANNER_ROWS)] = 0
            frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        elif not cap.grab():
            break
        i += 1
    cap.release()
    return frames


def handcrafted(frames: List[np.ndarray]) -> np.ndarray:
    """Per-frame flame statistics: brightness, bright-area fractions, colour ratios, vertical centroid."""
    rows = []
    for f in frames:
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
        body = g[int(g.shape[0] * BANNER_ROWS):]
        ys = np.nonzero(body > 0.35)[0]
        r, gc, b = (f[..., i].astype(np.float32).mean() + 1e-3 for i in range(3))
        rows.append([body.mean(), body.std(), (body > 0.2).mean(), (body > 0.5).mean(), (body > 0.8).mean(),
                     r / gc, b / gc, ys.mean() / body.shape[0] if len(ys) else 0.5])
    return np.asarray(rows, np.float32)


def video_features(path: str, cache_dir: Path, n_frames: int, device, arch: str = "resnet18") -> Dict[str, np.ndarray]:
    cache = cache_dir / (Path(path).stem[-60:] + f"_{n_frames}_{arch}.npz")
    if cache.exists():
        z = np.load(cache)
        return {k: z[k] for k in z.files}
    frames = sample_frames(path, n_frames)
    feats = {"emb": extract_embeddings(frames, device, arch=arch).numpy(), "hand": handcrafted(frames)}
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **feats)
    return feats


def pool(feats: Dict[str, np.ndarray], kind: str) -> np.ndarray:
    parts = []
    if kind in ("emb", "both"):
        e = feats["emb"]
        parts += [e.mean(0), e.std(0)]
    if kind in ("hand", "both"):
        h = feats["hand"]
        parts += [h.mean(0), h.std(0), np.percentile(h, 90, axis=0)]
    return np.concatenate(parts)


def loto_eval(X: np.ndarray, y: np.ndarray, groups: List[str], task: str, alphas=(10, 100, 1e3, 1e4, 1e5, 1e6)):
    """Leave-one-test-out. Alpha/C is chosen by an inner group-CV on the training tests only."""
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import FunctionTransformer, StandardScaler

    groups = np.asarray(groups)

    def make(a):
        est = Ridge(alpha=a) if task == "reg" else LogisticRegression(C=1.0 / a, max_iter=2000)
        return make_pipeline(StandardScaler(), FunctionTransformer(lambda z: np.clip(z, -5, 5)), est)

    def score(pred, true):
        return np.abs(pred - true).mean() if task == "reg" else -(pred == true).mean()

    preds = np.empty(len(y), dtype=y.dtype)
    chosen = []
    for g in np.unique(groups):
        tr, te = groups != g, groups == g
        best_a, best_s = alphas[0], np.inf
        for a in alphas:
            s = []
            for h in np.unique(groups[tr]):
                itr, ite = tr & (groups != h), tr & (groups == h)
                if len(np.unique(y[itr])) < 2 and task == "cls":
                    continue
                s.append(score(make(a).fit(X[itr], y[itr]).predict(X[ite]), y[ite]))
            if s and np.mean(s) < best_s:
                best_a, best_s = a, np.mean(s)
        chosen.append(best_a)
        if task == "cls" and len(np.unique(y[tr])) < 2:
            preds[te] = y[tr][0]
        else:
            preds[te] = make(best_a).fit(X[tr], y[tr]).predict(X[te])
    return preds, chosen


def run(videos_dir: str, table_csv: str, out_json: str, n_frames: int = 64, arch: str = "resnet18", cache_dir: str = "datasets/derived/cv_video_cache"):
    labels = load_labels(table_csv)
    paths = sorted(str(p) for p in Path(videos_dir).glob("*.mp4"))
    device = get_device()
    rows = []
    for p in paths:
        t = video_test_id(p)
        lab = labels.get(t)
        if lab is None:
            continue
        print("features", Path(p).name[-50:], flush=True)
        rows.append({"path": p, "group": t, **lab, "feats": video_features(p, Path(cache_dir), n_frames, device, arch)})
    groups = [r["group"] for r in rows]
    report = {"nVideos": len(rows), "nTests": len(set(groups)), "nFramesPerVideo": n_frames, "backbone": arch, "device": str(device),
              "protocol": "leave-one-test-out, inner group-CV for regularisation", "tasks": {}}

    have_o2 = [r for r in rows if r["o2"] is not None]
    y_o2 = np.array([r["o2"] for r in have_o2])
    g_o2 = [r["group"] for r in have_o2]
    base = np.abs(y_o2 - y_o2.mean()).mean()
    res = {"baselineMeanMAE": round(float(base), 3), "models": {}}
    for kind in ("hand", "emb", "both"):
        X = np.stack([pool(r["feats"], kind) for r in have_o2])
        pred, ch = loto_eval(X, y_o2, g_o2, "reg")
        res["models"][kind] = {"MAE": round(float(np.abs(pred - y_o2).mean()), 3),
                               "beatsBaseline": bool(np.abs(pred - y_o2).mean() < base)}
    report["tasks"]["initialO2_regression"] = {"n": len(have_o2), **res}

    fams = np.array([r["fuel"] for r in rows])
    maj = max(set(fams), key=list(fams).count)
    res = {"baselineMajorityAcc": round(float((fams == maj).mean()), 3), "classes": sorted(set(fams.tolist())), "models": {}}
    for kind in ("hand", "emb", "both"):
        X = np.stack([pool(r["feats"], kind) for r in rows])
        pred, ch = loto_eval(X, fams, groups, "cls")
        res["models"][kind] = {"accuracy": round(float((pred == fams).mean()), 3)}
    report["tasks"]["fuelFamily_classification"] = {"n": len(rows), **res}
    report["limitations"] = [
        f"Only {len(set(groups))} independent tests; estimates have very high variance.",
        "Fuel-family classes are mostly singletons, so held-out classes are unseen at test time.",
        "Telemetry overlay rows are masked so the model cannot read test identity from text.",
    ]
    Path(out_json).write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", default="datasets/raw/psi_api/PSI-25/Raw Data")
    ap.add_argument("--table", default="datasets/raw/psi_api/PSI-25/Experimental table/PSI-25_Experimental table_BASS-II.csv")
    ap.add_argument("--out", default="cv/contracts/training_report.json")
    ap.add_argument("--frames", type=int, default=64)
    ap.add_argument("--arch", default="resnet18")
    a = ap.parse_args()
    print(json.dumps(run(a.videos, a.table, a.out, a.frames, a.arch), indent=2))
