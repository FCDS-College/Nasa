"""
gold.py - The CV evaluation set (cv_gold_v1): frame-level flame labels and flame masks, and the runner that
scores the served pipeline against them (CV audit finding CV-3).

Labels are drafted, then verified by a person. Every item records who labelled it and whether a person has
verified it, and the report gives numbers for all items and for verified items separately. Splits are by
test (``groupId``): ``holdout`` holds tests that were never used to choose a threshold.

    python -m cv.gold fetch                 # download the held-out videos (not in Git), verify SHA-256
    python -m cv.gold frames                # extract every labelled frame to datasets/derived/cv_gold/frames
    python -m cv.gold draft-mask ITEM X0 Y0 X1 Y1   # GrabCut mask from a box drawn around the flame
    python -m cv.gold review                # overlays for checking + the review sheet
    python -m cv.gold adopt                 # apply a filled-in review sheet (marks items verified)
    python -m cv.gold evaluate              # score the pipeline; writes cv/contracts/gold_evaluation_report.json

Masks are in ORIGINAL image pixels (binary PNG, 255 = flame). Video items are scored through the served
video path (overlay mask included) at exactly the sampled frame indexes.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import io
import json
import random
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

from cv.flame_cv import (PIPELINE_VERSION, CVConfig, Letterbox, _to_rgb8, analyze_image_safe, atomic_write_text,
                         compute_auto_target_size, letterbox_geometry, utc_now, with_camera_profile)
from cv.video_analysis import analyze_video
from cv.video_ingestion import VIDEO_PIPELINE_VERSION, VideoConfig, iter_frames, probe_video, sampled_indexes

GOLD_VERSION = "cv_gold_v1"
SOURCES_PATH = Path("datasets/evaluation/cv_gold_v1_sources.json")
GOLD_PATH = Path("datasets/evaluation/cv_gold_v1.jsonl")
MASK_DIR = Path("datasets/evaluation/cv_gold_v1_masks")
REVIEW_PATH = Path("datasets/evaluation/cv_gold_v1_review.csv")
FRAMES_DIR = Path("datasets/derived/cv_gold/frames")
REVIEW_IMAGES_DIR = Path("datasets/derived/cv_gold/review")
REPORT_PATH = Path("cv/contracts/gold_evaluation_report.json")
LABELS = ("present", "absent", "unclear")
COHORTS = ("v1", "v2-dim", "v2-flex")   # v1: the original set; v2-*: the held-out cohort of CV_HELDOUT_V2_PLAN.md
SELECTION_PATH = Path("datasets/evaluation/cv_gold_v2_selection.json")
SELECTION_SEED = 20261114
LOCALIZED_IOU = 0.1
REVIEW_FIELDS = ["itemId", "split", "groupId", "draftLabel", "hasMask", "reviewImage",
                 "verdict", "correctedLabel", "maskOk", "reviewer", "notes"]


# --------------------------------------------------------------------------------------- loading
def sha256_hex(path: Any) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_sources(path: Any = SOURCES_PATH) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_gold(path: Any = GOLD_PATH) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def save_gold(items: Iterable[Dict[str, Any]], path: Any = GOLD_PATH) -> None:
    ordered = sorted(items, key=lambda i: (i["split"], i["groupId"], i["itemId"]))
    atomic_write_text(path, "".join(json.dumps(i, sort_keys=True) + "\n" for i in ordered))


@dataclass(frozen=True)
class ItemRef:
    item_id: str
    source: Dict[str, Any]
    frame_index: Optional[int]


def video_config(source: Dict[str, Any]) -> VideoConfig:
    s = source["sampling"]
    # maxDurationS lifts the API's 600 s upload limit for a long source (a full NASA test video). The per-frame
    # analysis, sampling and overlay masking are the same; only the upload guard differs.
    extra = {"max_duration_s": float(s["maxDurationS"])} if s.get("maxDurationS") else {}
    return VideoConfig(sample_every=s["sampleEvery"], max_frames=s["maxFrames"], **extra)


def enumerate_items(sources_doc: Dict[str, Any]) -> List[ItemRef]:
    """Every frame to label: one per image, and the served sampling grid of each video."""
    refs: List[ItemRef] = []
    for src in sources_doc["sources"]:
        if src["kind"] == "image":
            refs.append(ItemRef(src["sourceId"], src, None))
        else:
            for idx in sampled_indexes(src["sampling"]["frameCount"], video_config(src)):
                refs.append(ItemRef(f"{src['sourceId']}-f{idx:06d}", src, idx))
    return refs


# --------------------------------------------------------------------------------------- fetching / frames
def _psi_download_module():
    path = Path(__file__).resolve().parents[1] / "knowledge" / "ingestion" / "psi_download.py"
    spec = importlib.util.spec_from_file_location("psi_download", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _psi_row(meta: Dict[str, Any], size_bytes: int) -> Dict[str, str]:
    return {"psi_id": meta["psiId"], "file_name": meta["fileName"], "file_version": meta["version"],
            "size_bytes": str(size_bytes), "object_key": f"psi-data/{meta['psiId']}/Raw Data/{meta['fileName']}"}


ZIP_FRAMES_DIR = Path("datasets/raw/psi_api/PSI-69/frames")


def zip_frame_path(zip_name: str, member: str) -> Path:
    """Where a frame extracted from a NASA zip is kept (lossless PNG, not in Git)."""
    stem = Path(zip_name).stem.split("_")[-1]
    return ZIP_FRAMES_DIR / stem / (Path(member).stem + ".png")


def extract_zip_member(zip_path: Any, member: str, out_png: Any) -> str:
    """Write one zip member as a lossless PNG; return the SHA-256 of the member's original bytes."""
    with zipfile.ZipFile(zip_path) as zf:
        data = zf.read(member)
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(data)) as im:
        im.save(out_png, format="PNG")
    return hashlib.sha256(data).hexdigest()


def sample_members(names: Sequence[str], k: int = 15) -> List[str]:
    """k frames evenly spaced over the sorted image members (first and last included), as the committed samples."""
    frames = sorted(n for n in names if n.lower().endswith((".bmp", ".png", ".tif", ".tiff")))
    if len(frames) <= k:
        return frames
    return [frames[round(i * (len(frames) - 1) / (k - 1))] for i in range(k)]


def _fetch_zip_members(srcs: List[Dict[str, Any]], psi, delete_zip: bool = True) -> List[Tuple[str, str]]:
    """Extract the recorded members of one zip (downloading it if a frame is missing) and check their SHA-256."""
    meta = srcs[0]["zip"]
    missing = [s for s in srcs if not Path(s["path"]).exists()]
    out = []
    if missing:
        row = _psi_row(meta["psi"], meta["sizeBytes"])
        status = psi.download(row)[0]
        zip_path = psi.local_path(row)
        for s in srcs:
            digest = extract_zip_member(zip_path, s["zip"]["member"], s["path"])
            if digest != s["zip"]["memberSha256"]:
                raise RuntimeError(f"{s['sourceId']}: checksum mismatch for member {s['zip']['member']}")
            out.append((s["sourceId"], status))
        if delete_zip:
            Path(zip_path).unlink(missing_ok=True)
    else:
        out += [(s["sourceId"], "present") for s in srcs]
    return out


def fetch(sources_doc: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Download sources that are not in Git and check them against the manifest's SHA-256.

    A source with a `zip` block is one frame of a NASA zip: the zip is downloaded only if a recorded frame is
    missing, the recorded members are extracted as PNG and checked against their SHA-256, and the zip is deleted.
    """
    psi = _psi_download_module()
    out = []
    by_zip: Dict[str, List[Dict[str, Any]]] = {}
    for src in sources_doc["sources"]:
        if src.get("zip"):
            by_zip.setdefault(src["zip"]["psi"]["fileName"], []).append(src)
    for srcs in by_zip.values():
        out += _fetch_zip_members(srcs, psi)
    for src in sources_doc["sources"]:
        if src["inGit"] or src.get("zip"):
            continue
        meta = src["psi"]
        row = {"psi_id": meta["psiId"], "file_name": meta["fileName"], "file_version": meta["version"],
               "size_bytes": str(src["sizeBytes"]), "object_key": f"psi-data/{meta['psiId']}/Raw Data/{meta['fileName']}"}
        if psi.local_path(row).resolve() != Path(src["path"]).resolve():
            raise RuntimeError(f"{src['sourceId']}: downloader path {psi.local_path(row)} differs from {src['path']}")
        status = psi.download(row)[0]
        ok = sha256_hex(src["path"]) == src["sha256"]
        out.append((src["sourceId"], f"{status}{'' if ok else ' CHECKSUM MISMATCH'}"))
        if not ok:
            raise RuntimeError(f"{src['sourceId']}: checksum mismatch for {src['path']}")
    return out


def load_rgb(path: Any) -> np.ndarray:
    """RGB uint8 exactly as the pipeline sees an image (EXIF orientation applied, 16-bit scaled)."""
    with Image.open(path) as im:
        return np.asarray(_to_rgb8(ImageOps.exif_transpose(im), CVConfig()), dtype=np.uint8)


def extract_frames(sources_doc: Dict[str, Any], out_dir: Any = FRAMES_DIR) -> Dict[str, Path]:
    """Write every item's frame as a PNG (RGB as the pipeline sees it, before any overlay mask)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Path] = {}
    by_source: Dict[str, List[ItemRef]] = {}
    for ref in enumerate_items(sources_doc):
        by_source.setdefault(ref.source["sourceId"], []).append(ref)
    for refs in by_source.values():
        src = refs[0].source
        if src["kind"] == "image":
            target = out_dir / f"{refs[0].item_id}.png"
            Image.fromarray(load_rgb(src["path"])).save(target)
            paths[refs[0].item_id] = target
            continue
        cfg = video_config(src)
        record = probe_video(src["path"], cfg)
        wanted = {r.frame_index: r.item_id for r in refs}
        for frame in iter_frames(src["path"], record, cfg):
            if frame.frameIndex in wanted:
                target = out_dir / f"{wanted[frame.frameIndex]}.png"
                cv2.imwrite(str(target), frame.image)
                paths[wanted[frame.frameIndex]] = target
    return paths


# --------------------------------------------------------------------------------------- masks
def draft_mask(image: np.ndarray, box: Sequence[int], iterations: int = 5) -> np.ndarray:
    """GrabCut segmentation seeded by a box drawn around the flame (box = x0, y0, x1, y1, original pixels).

    A different algorithm from the pipeline's global Otsu threshold, and the box comes from the labeller, so
    hardware and overlays outside it can never enter the mask. Returns 0/255 uint8.
    """
    img = image if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    h, w = img.shape[:2]
    x0, y0, x1, y1 = (int(v) for v in box)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1 - x0 < 3 or y1 - y0 < 3:
        raise ValueError("box is too small")
    gc = np.zeros((h, w), np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(np.ascontiguousarray(img), gc, (x0, y0, x1 - x0, y1 - y0), bgd, fgd, iterations, cv2.GC_INIT_WITH_RECT)
    mask = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    outside = np.ones((h, w), bool)
    outside[y0:y1, x0:x1] = False
    mask[outside] = 0
    return mask


def threshold_mask(image: np.ndarray, box: Sequence[int]) -> np.ndarray:
    """Otsu threshold inside the box, on the box's own contrast range. For dim flames (a faint blue crescent)
    where GrabCut has too little colour contrast to separate anything. Returns 0/255 uint8."""
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    x0, y0, x1, y1 = max(0, int(box[0])), max(0, int(box[1])), min(w, int(box[2])), min(h, int(box[3]))
    crop = cv2.GaussianBlur(gray[y0:y1, x0:x1], (3, 3), 0).astype(np.float32)
    lo, hi = np.percentile(crop, 5), np.percentile(crop, 99.5)
    if hi - lo < 1:
        return np.zeros((h, w), np.uint8)
    stretched = np.clip((crop - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
    _, inner = cv2.threshold(stretched, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inner = cv2.morphologyEx(inner, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    mask = np.zeros((h, w), np.uint8)
    mask[y0:y1, x0:x1] = inner
    return mask


MASK_METHODS = {"grabcut-from-box": draft_mask, "threshold-in-box": threshold_mask}


def letterbox_for(width: int, height: int) -> Letterbox:
    return letterbox_geometry(width, height, compute_auto_target_size(width, height))


def to_letterbox(mask: np.ndarray, lb: Letterbox) -> np.ndarray:
    """An original-pixel mask placed on the pipeline's letterbox canvas (nearest neighbour, like letterbox_mask)."""
    resized = cv2.resize(mask, (lb.new_w, lb.new_h), interpolation=cv2.INTER_NEAREST)
    canvas = np.zeros((lb.target, lb.target), np.uint8)
    canvas[lb.pad_y:lb.pad_y + lb.new_h, lb.pad_x:lb.pad_x + lb.new_w] = resized
    return (canvas > 127).astype(np.uint8) * 255


def mask_iou(pred: np.ndarray, truth: np.ndarray) -> float:
    p, t = pred > 0, truth > 0
    union = np.logical_or(p, t).sum()
    return 1.0 if union == 0 else float(np.logical_and(p, t).sum() / union)


# --------------------------------------------------------------------------------------- metrics
def _ratio(a: int, b: int) -> Optional[float]:
    return round(a / b, 4) if b else None


def detection_metrics(rows: Iterable[Tuple[str, str]], positive: set) -> Dict[str, Any]:
    """rows = (label, predicted status). ``unclear`` labels are excluded."""
    tp = fp = fn = tn = 0
    for label, status in rows:
        if label == "unclear":
            continue
        hit = status in positive
        if label == "present":
            tp, fn = tp + hit, fn + (not hit)
        else:
            fp, tn = fp + hit, tn + (not hit)
    precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
    f1 = round(2 * precision * recall / (precision + recall), 4) if precision and recall else (
        0.0 if precision is not None and recall is not None else None)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1,
            "falsePositiveRate": _ratio(fp, fp + tn)}


def group_bootstrap(rows: Sequence[Tuple[str, Any]], stat: Callable[[List[Any]], Optional[float]],
                    reps: int = 2000, seed: int = 0) -> Tuple[Optional[float], Optional[float]]:
    """95% percentile interval, resampling whole groups (tests) with replacement, never single frames."""
    groups: Dict[str, List[Any]] = {}
    for g, v in rows:
        groups.setdefault(g, []).append(v)
    if not groups:
        return None, None
    keys = sorted(groups)
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(reps):
        sample = [v for k in rng.choice(keys, size=len(keys), replace=True) for v in groups[k]]
        s = stat(sample)
        if s is not None:
            values.append(s)
    if not values:
        return None, None
    return round(float(np.percentile(values, 2.5)), 4), round(float(np.percentile(values, 97.5)), 4)


def cohort_of(item: Dict[str, Any]) -> str:
    """The item's cohort; items written before cohorts existed are v1."""
    return item.get("cohort") or "v1"


def binomial_upper(successes: int, n: int, level: float = 0.95) -> Optional[float]:
    """Exact (Clopper-Pearson) one-sided upper bound on a proportion, by bisection on the binomial CDF."""
    if n == 0:
        return None
    if successes >= n:
        return 1.0
    alpha = 1 - level
    def cdf(p):   # P(X <= successes | n, p)
        term, total = (1 - p) ** n, 0.0
        for k in range(successes + 1):
            total += term
            term = term * (n - k) / (k + 1) * p / (1 - p) if p < 1 else 0.0
        return total
    lo, hi = successes / n, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) > alpha else (lo, mid)
    return round(hi, 4)


def _test_level_false_positives(rows: List[Dict[str, Any]], positive: set) -> Dict[str, Any]:
    """Tests with at least one false-positive frame among their absent frames; frames within a test are strongly
    correlated (ICC 0.76-0.87 on cv_gold_v1), so the test is the unit for a bound."""
    tests: Dict[str, bool] = {}
    for r in rows:
        if r["label"] == "absent":
            tests[r["groupId"]] = tests.get(r["groupId"], False) or r["status"] in positive
    k, j = len(tests), sum(tests.values())
    return {"tests": k, "testsWithFalsePositive": j, "rate": _ratio(j, k), "upper95": binomial_upper(j, k)}


def _summary(rows: List[Dict[str, Any]], reps: int, seed: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {"n": len(rows), "nTests": len({r["groupId"] for r in rows}),
                           "labels": {k: sum(r["label"] == k for r in rows) for k in LABELS}}
    def localized(r):
        # On a flame frame, PRESENT only counts if the pipeline's mask overlaps the labelled flame (IoU >= 0.1);
        # otherwise a box on the telemetry overlay of a flame frame would count as finding the flame.
        if r["label"] == "present" and r["status"] == "PRESENT" and r.get("iou") is not None and r["iou"] < LOCALIZED_IOU:
            return "MISPLACED"
        return r["status"]

    variants = {"strict": ({"PRESENT"}, lambda r: r["status"]),
                "lenient": ({"PRESENT", "UNCERTAIN"}, lambda r: r["status"]),
                "localized": ({"PRESENT"}, localized)}
    det = {}
    for name, (positive, status_of) in variants.items():
        pairs = [(r["groupId"], (r["label"], status_of(r))) for r in rows]
        m = detection_metrics([p for _, p in pairs], positive)
        for metric in ("precision", "recall", "falsePositiveRate"):
            m[f"{metric}CI95"] = list(group_bootstrap(pairs, lambda s, p=positive, k=metric: detection_metrics(s, p)[k],
                                                      reps, seed))
        m["testLevelFalsePositives"] = _test_level_false_positives(rows, positive)
        det[name] = m
    out["detection"] = det
    out["nVerified"] = sum(1 for r in rows if r.get("verified"))
    seg = [(r["groupId"], r["iou"]) for r in rows if r.get("iou") is not None]
    seg_det = [(g, v) for (g, v), r in zip(seg, [r for r in rows if r.get("iou") is not None]) if r["status"] == "PRESENT"]
    mean = lambda s: float(np.mean(s)) if s else None  # noqa: E731
    out["segmentation"] = {
        "n": len(seg), "meanIoU": round(mean([v for _, v in seg]), 4) if seg else None,
        "meanIoUCI95": list(group_bootstrap(seg, mean, reps, seed)),
        "nDetected": len(seg_det), "meanIoUWhenDetected": round(mean([v for _, v in seg_det]), 4) if seg_det else None,
        "note": "IoU on the pipeline's letterbox canvas; a missed flame counts as IoU 0 in meanIoU. The pipeline "
                "keeps only the largest region, so multi-lobe flames lower IoU."}
    return out


# --------------------------------------------------------------------------------------- evaluation
def _predict_source(src: Dict[str, Any], work: Path, cfg: Optional[CVConfig]) -> Dict[Optional[int], Dict[str, Any]]:
    """frameIndex (None for an image) -> {status, confidence, maskPath, lb}."""
    if src["kind"] == "image":
        request = {"imagePath": src["path"], "imageId": src["sourceId"]}
        if src.get("cameraProfile"):   # as an API client sending camera_profile would
            request["metadata"] = {"cameraProfile": src["cameraProfile"]}
        res = analyze_image_safe(request, work / "cv", work / "masks",
                                 cfg=cfg)
        if res.get("status") != "SUCCESS":
            return {None: {"status": "ERROR", "confidence": None, "maskPath": None, "lb": None,
                           "error": res["error"]["code"]}}
        pre = res["preprocessing"]
        return {None: {"status": res["detection"]["status"], "confidence": res["detection"]["confidence"],
                       "maskPath": res["segmentation"].get("maskUri"),
                       "lb": letterbox_geometry(pre["originalWidth"], pre["originalHeight"], pre["targetSize"])}}
    if src.get("cameraProfile"):
        cfg = with_camera_profile(cfg or CVConfig(), src["cameraProfile"])
    result = analyze_video(src["path"], work, cfg=cfg, video_cfg=video_config(src), resume=False)
    w, h = result["videoMetadata"]["resolution"]
    job = work / result["videoId"]
    out = {}
    for f in result["frameMeasurements"]:
        mask = job / "masks" / f"{f['frameId']}_mask.png"
        out[f["frameIndex"]] = {"status": f["detectionStatus"], "confidence": f.get("detectionConfidence"),
                                "maskPath": str(mask) if mask.exists() else None, "lb": letterbox_for(w, h)}
    return out


def evaluate(sources_doc: Dict[str, Any], items: List[Dict[str, Any]], work_dir: Any,
             cfg: Optional[CVConfig] = None, reps: int = 2000, seed: int = 0) -> Dict[str, Any]:
    work_dir = Path(work_dir)
    sources = {s["sourceId"]: s for s in sources_doc["sources"]}
    predictions: Dict[str, Dict[Optional[int], Dict[str, Any]]] = {}
    rows = []
    for item in sorted(items, key=lambda i: i["itemId"]):
        sid = item["sourceId"]
        if sid not in predictions:
            predictions[sid] = _predict_source(sources[sid], work_dir / sid, cfg)
        pred = predictions[sid].get(item["frameIndex"])
        if pred is None:
            raise RuntimeError(f"{item['itemId']}: frame {item['frameIndex']} was not sampled by the pipeline")
        row = {"itemId": item["itemId"], "groupId": item["groupId"], "split": item["split"], "label": item["label"],
               "cohort": cohort_of(item),
               "status": pred["status"], "confidence": pred["confidence"],
               "verified": bool(item["provenance"]["verified"]), "iou": None}
        if item["label"] == "present" and item["mask"] and pred["lb"] is not None:
            truth = cv2.imread(str(item["mask"]["uri"]), cv2.IMREAD_GRAYSCALE)
            gt = to_letterbox(truth, pred["lb"])
            if pred["status"] == "PRESENT" and pred["maskPath"]:
                pm = cv2.imread(pred["maskPath"], cv2.IMREAD_GRAYSCALE)
            else:
                pm = np.zeros_like(gt)
            row["iou"] = round(mask_iou(pm, gt), 4)
        rows.append(row)
    splits = {}
    for split in sorted({r["split"] for r in rows}):
        in_split = [r for r in rows if r["split"] == split]
        splits[split] = {"all": _summary(in_split, reps, seed),
                         "verified": _summary([r for r in in_split if r["verified"]], reps, seed)}
    cohorts = {}
    for cohort in sorted({r["cohort"] for r in rows}):
        in_cohort = [r for r in rows if r["cohort"] == cohort]
        cohorts[cohort] = {"all": _summary(in_cohort, reps, seed),
                           "verified": _summary([r for r in in_cohort if r["verified"]], reps, seed)}
    cfg = cfg or CVConfig()
    return {"goldVersion": GOLD_VERSION, "generatedAt": utc_now(), "pipelineVersion": PIPELINE_VERSION,
            "videoPipelineVersion": VIDEO_PIPELINE_VERSION, "configDigest": cfg.digest(),
            "protocol": "Detection: strict counts PRESENT as positive, lenient counts PRESENT or UNCERTAIN, localized "
                        "also requires the mask on a flame frame to overlap the labelled flame (IoU >= 0.1); unclear "
                        "labels are excluded. 95% intervals resample whole tests (groupId), not frames. 'verified' "
                        "uses only items a person has checked.",
            "splits": splits, "cohorts": cohorts, "items": rows}


# --------------------------------------------------------------------------------------- cohort 2 selection
INVENTORY_PATH = Path("datasets/manifests/psi_all_combustion_inventory.csv")
FLEX_TABLE_PATH = Path("datasets/raw/psi_api/PSI-69/Experimental table/PSI-69_Experimental table_FLEX.csv")
BASS_TABLE_PATH = Path("datasets/raw/psi_api/PSI-25/Experimental table/PSI-25_Experimental table_BASS-II.csv")
DEV_FLEX_SEQUENCES = ("176F001", "195F002", "H08M101", "X168M03", "X177H10")
USED_MILLER_TESTS = ("M10", "M16", "M19")
FLEX_COHORT_SIZE = 30


def _proportional(counts: Dict[str, int], total: int) -> Dict[str, int]:
    """Largest-remainder allocation of `total` over strata, at least one per non-empty stratum."""
    pool = sum(counts.values())
    quota = {k: max(1, total * v / pool) for k, v in counts.items()}
    alloc = {k: min(counts[k], int(q)) for k, q in quota.items()}
    order = sorted(counts, key=lambda k: (-(quota[k] - int(quota[k])), k))
    i = 0
    while sum(alloc.values()) < min(total, pool) and i < 10 * len(order):
        k = order[i % len(order)]
        if alloc[k] < counts[k]:
            alloc[k] += 1
        i += 1
    return alloc


def select_cohorts(inventory: List[Dict[str, str]], flex_table: List[Dict[str, str]], bass_table: List[List[str]],
                   seed: int = SELECTION_SEED, flex_size: int = FLEX_COHORT_SIZE) -> Dict[str, Any]:
    """Cohort 2 from metadata only (no frame is opened): every unused Miller test, and FLEX colour sequences drawn
    with a fixed seed, stratified by ID series x fuel. See docs/plan/CV_HELDOUT_V2_PLAN.md (sections 4.1 and 5.1)."""
    rng = random.Random(seed)
    # Dim flames: Miller main-view videos (not the second view, not LOS portions or still sequences).
    days = {r[1].strip(): r[3].strip() for r in bass_table[1:] if len(r) > 3 and re.fullmatch(r"M\d+", r[1].strip())}
    miller = {}
    for r in inventory:
        m = re.fullmatch(r"PSI-25_Raw Data_BASS_GMT\d+_SAMPLE_\w+_TEST_(M\d+)\.mp4", r["file_name"])
        if m and m.group(1) not in USED_MILLER_TESTS:
            miller[m.group(1)] = {"test": m.group(1), "fileName": r["file_name"], "version": r["file_version"],
                                  "sizeBytes": int(r["size_bytes"]), "gmtDay": days.get(m.group(1))}
    dim = [miller[k] for k in sorted(miller, key=lambda t: int(t[1:]))]
    # FLEX colour sequences that match a table row.
    table = {r["FLEX Identifier"].strip(): r for r in flex_table}
    zips = {}
    for r in inventory:
        m = re.search(r"_([0-9A-Z]{7})D\.zip$", r["file_name"])
        if r["psi_id"] == "PSI-69" and r["category"] == "Raw Data" and m and m.group(1) in table \
                and m.group(1) not in DEV_FLEX_SEQUENCES:
            zips[m.group(1)] = r
    def stratum(seq_id):
        series = "numeric" if seq_id[0].isdigit() else seq_id[0]
        return f"{series}/{table[seq_id]['Fuel'].strip()}"
    strata: Dict[str, List[str]] = {}
    for seq_id in sorted(zips):
        strata.setdefault(stratum(seq_id), []).append(seq_id)
    alloc = _proportional({k: len(v) for k, v in strata.items()}, flex_size)
    chosen = []
    for k in sorted(strata):
        chosen += sorted(rng.sample(strata[k], alloc[k]))
    def flex_entry(seq_id):
        z, t = zips[seq_id], table[seq_id]
        col = lambda prefix: next((v for c, v in t.items() if c.startswith(prefix)), None)  # noqa: E731
        return {"sequence": seq_id, "stratum": stratum(seq_id), "fileName": z["file_name"], "version": z["file_version"],
                "sizeBytes": int(z["size_bytes"]), "fuel": t["Fuel"].strip(), "testEnd": t.get("Test end", "").strip(),
                "burnTimeS": col("Burn time"), "dropletInitialDiameterMm": col("Droplet initial")}
    return {"seed": seed, "plan": "docs/plan/CV_HELDOUT_V2_PLAN.md",
            "rule": {"dim": "every unused BASS-II Miller main-view video (M10, M16, M19 excluded)",
                     "flex": f"{flex_size} FLEX colour sequences matching the FLEX table, minus the 5 dev sequences, "
                             "stratified by ID series x fuel (largest remainder, >= 1 per stratum), random.Random(seed)"},
            "dim": {"poolSize": len(dim), "selected": dim},
            "flex": {"poolSize": len(zips), "strata": {k: {"pool": len(v), "selected": alloc[k]} for k, v in sorted(strata.items())},
                     "selected": [flex_entry(s) for s in chosen]}}


# --------------------------------------------------------------------------------------- review / adopt
def write_review_sheet(items: List[Dict[str, Any]], csv_path: Any = REVIEW_PATH,
                       images_dir: Any = REVIEW_IMAGES_DIR) -> Path:
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_FIELDS)
        w.writeheader()
        for item in sorted(items, key=lambda i: (i["split"], i["groupId"], i["itemId"])):
            w.writerow({"itemId": item["itemId"], "split": item["split"], "groupId": item["groupId"],
                        "draftLabel": item["label"], "hasMask": "yes" if item["mask"] else "no",
                        "reviewImage": (Path(images_dir) / f"{item['itemId']}.png").as_posix(),
                        "verdict": "", "correctedLabel": "", "maskOk": "", "reviewer": "", "notes": ""})
    return csv_path


def render_review_images(items: List[Dict[str, Any]], frames_dir: Any = FRAMES_DIR,
                         out_dir: Any = REVIEW_IMAGES_DIR) -> int:
    """Frame | frame with the draft mask outlined, labelled with the draft label, one PNG per item."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for item in items:
        frame = cv2.imread(str(Path(frames_dir) / f"{item['itemId']}.png"))
        if frame is None:
            continue
        marked = frame.copy()
        if item["mask"]:
            m = cv2.imread(str(item["mask"]["uri"]), cv2.IMREAD_GRAYSCALE)
            contours, _ = cv2.findContours((m > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(marked, contours, -1, (0, 255, 0), 1)
        both = np.hstack([frame, marked])
        text = f"{item['itemId']}  draft: {item['label']}{'  (mask)' if item['mask'] else ''}"
        cv2.putText(both, text, (8, both.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.imwrite(str(out_dir / f"{item['itemId']}.png"), both)
        n += 1
    return n


def adopt_review(items: List[Dict[str, Any]], csv_path: Any = REVIEW_PATH,
                 now: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Apply a filled-in review sheet. verdict: accept | fix | (blank/unsure = skip)."""
    now = now or utc_now()
    reviews = {r["itemId"]: r for r in csv.DictReader(Path(csv_path).open(encoding="utf-8"))}
    summary = {"accepted": 0, "fixed": 0, "skipped": 0, "maskRejected": 0}
    out = []
    for item in items:
        item = copy.deepcopy(item)
        r = reviews.get(item["itemId"])
        verdict = (r or {}).get("verdict", "").strip().lower()
        if verdict not in ("accept", "fix"):
            summary["skipped"] += 1
            out.append(item)
            continue
        reviewer = r.get("reviewer", "").strip()
        if not reviewer:
            raise ValueError(f"{item['itemId']}: a reviewed row needs a reviewer name")
        if verdict == "fix":
            new_label = r.get("correctedLabel", "").strip().lower()
            if new_label not in LABELS:
                raise ValueError(f"{item['itemId']}: correctedLabel must be one of {LABELS}")
            item["label"] = new_label
            if new_label != "present":
                item["mask"] = None
            summary["fixed"] += 1
        else:
            summary["accepted"] += 1
        notes = r.get("notes", "").strip()
        verified = True
        if item["mask"] and r.get("maskOk", "").strip().lower() == "no":
            item["mask"] = None
            verified = False
            notes = "; ".join(x for x in (notes, "mask rejected by reviewer; needs a redrawn mask") if x)
            summary["maskRejected"] += 1
        if notes:
            item["notes"] = "; ".join(x for x in (item.get("notes", ""), notes) if x)
        item["provenance"].update(verified=verified, verifiedBy=reviewer if verified else None,
                                  verifiedAt=now if verified else None)
        out.append(item)
    return out, summary


# --------------------------------------------------------------------------------------- CLI
def _markdown(report: Dict[str, Any]) -> str:
    lines = [f"Pipeline `{report['pipelineVersion']}` / `{report['videoPipelineVersion']}`, generated "
             f"{report['generatedAt']}.", "",
             "| Split | Subset | Frames (tests) | present / absent / unclear | Precision | Recall | Localized recall | "
             "False-positive rate | Mean mask IoU |", "|---|---|---|---|---|---|---|---|---|"]

    def fmt(v, ci):
        return "n/a" if v is None else (f"{v:.2f} [{ci[0]:.2f}, {ci[1]:.2f}]" if ci and ci[0] is not None else f"{v:.2f}")
    blocks = [(f"split {k}", v) for k, v in report["splits"].items()]
    blocks += [(f"cohort {k}", v) for k, v in report.get("cohorts", {}).items()]
    for split, subsets in blocks:
        for subset, s in subsets.items():
            d, g, loc = s["detection"]["strict"], s["segmentation"], s["detection"]["localized"]
            lab = s["labels"]
            subset = f"{subset} ({s.get('nVerified', 0)} verified)" if subset == "all" else subset
            lines.append(f"| {split} | {subset} | {s['n']} ({s['nTests']}) | {lab['present']} / {lab['absent']} / "
                         f"{lab['unclear']} | {fmt(d['precision'], d['precisionCI95'])} | {fmt(d['recall'], d['recallCI95'])} | "
                         f"{fmt(loc['recall'], loc['recallCI95'])}"
                         f" | {fmt(d['falsePositiveRate'], d['falsePositiveRateCI95'])} | {fmt(g['meanIoU'], g['meanIoUCI95'])} |")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cv.gold", description="The CV evaluation set (cv_gold_v1).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    sub.add_parser("frames")
    dm = sub.add_parser("draft-mask")
    dm.add_argument("item")
    dm.add_argument("box", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"))
    dm.add_argument("--method", choices=sorted(MASK_METHODS), default="grabcut-from-box")
    sub.add_parser("review")
    ad = sub.add_parser("adopt")
    ad.add_argument("--sheet", default=str(REVIEW_PATH))
    sub.add_parser("select", help="write the cohort-2 selection from metadata only (no frame is opened)")
    ev = sub.add_parser("evaluate")
    ev.add_argument("--work-dir", default="datasets/derived/cv_gold/eval")
    ev.add_argument("--out", default=str(REPORT_PATH))
    args = ap.parse_args(argv)

    if args.cmd == "select":
        inventory = list(csv.DictReader(INVENTORY_PATH.open(encoding="utf-8")))
        flex_table = list(csv.DictReader(FLEX_TABLE_PATH.open(encoding="cp1252")))
        bass_table = list(csv.reader(BASS_TABLE_PATH.open(encoding="cp1252")))
        selection = select_cohorts(inventory, flex_table, bass_table)
        selection["createdAt"] = utc_now()
        atomic_write_text(SELECTION_PATH, json.dumps(selection, indent=1, ensure_ascii=False) + "\n")
        print(f"{SELECTION_PATH}: {len(selection['dim']['selected'])} dim-flame tests, "
              f"{len(selection['flex']['selected'])} FLEX sequences")
        return 0
    sources = load_sources()
    if args.cmd == "fetch":
        for sid, status in fetch(sources):
            print(sid, status)
    elif args.cmd == "frames":
        print(f"{len(extract_frames(sources))} frames written to {FRAMES_DIR}")
    elif args.cmd == "draft-mask":
        items = {i["itemId"]: i for i in load_gold()}
        item = items[args.item]
        frame = cv2.imread(str(FRAMES_DIR / f"{args.item}.png"))
        if frame is None:
            print(f"frame missing: run `python -m cv.gold frames` first", file=sys.stderr)
            return 1
        mask = MASK_METHODS[args.method](frame, args.box)
        MASK_DIR.mkdir(parents=True, exist_ok=True)
        target = MASK_DIR / f"{args.item}.png"
        cv2.imwrite(str(target), mask)
        item["label"] = "present"
        item["mask"] = {"uri": target.as_posix(), "method": args.method, "box": list(args.box)}
        item["provenance"].update(verified=False, verifiedBy=None, verifiedAt=None)
        save_gold(items.values())
        print(f"{target}: {int((mask > 0).sum())} pixels")
    elif args.cmd == "review":
        items = load_gold()
        n = render_review_images(items)
        print(f"{write_review_sheet(items)} ({len(items)} rows); {n} review images in {REVIEW_IMAGES_DIR}")
    elif args.cmd == "adopt":
        items, summary = adopt_review(load_gold(), args.sheet)
        save_gold(items)
        print(json.dumps(summary))
    elif args.cmd == "evaluate":
        report = evaluate(sources, load_gold(), args.work_dir)
        atomic_write_text(args.out, json.dumps(report, indent=2) + "\n")
        print(_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
