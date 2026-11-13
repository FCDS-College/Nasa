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
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

from cv.flame_cv import (PIPELINE_VERSION, CVConfig, Letterbox, _to_rgb8, analyze_image_safe, atomic_write_text,
                         compute_auto_target_size, letterbox_geometry, utc_now)
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
    return VideoConfig(sample_every=s["sampleEvery"], max_frames=s["maxFrames"])


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


def fetch(sources_doc: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Download sources that are not in Git and check them against the manifest's SHA-256."""
    psi = _psi_download_module()
    out = []
    for src in sources_doc["sources"]:
        if src["inGit"]:
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
        det[name] = m
    out["detection"] = det
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
        res = analyze_image_safe({"imagePath": src["path"], "imageId": src["sourceId"]}, work / "cv", work / "masks",
                                 cfg=cfg)
        if res.get("status") != "SUCCESS":
            return {None: {"status": "ERROR", "confidence": None, "maskPath": None, "lb": None,
                           "error": res["error"]["code"]}}
        pre = res["preprocessing"]
        return {None: {"status": res["detection"]["status"], "confidence": res["detection"]["confidence"],
                       "maskPath": res["segmentation"].get("maskUri"),
                       "lb": letterbox_geometry(pre["originalWidth"], pre["originalHeight"], pre["targetSize"])}}
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
    cfg = cfg or CVConfig()
    return {"goldVersion": GOLD_VERSION, "generatedAt": utc_now(), "pipelineVersion": PIPELINE_VERSION,
            "videoPipelineVersion": VIDEO_PIPELINE_VERSION, "configDigest": cfg.digest(),
            "protocol": "Detection: strict counts PRESENT as positive, lenient counts PRESENT or UNCERTAIN, localized "
                        "also requires the mask on a flame frame to overlap the labelled flame (IoU >= 0.1); unclear "
                        "labels are excluded. 95% intervals resample whole tests (groupId), not frames. 'verified' "
                        "uses only items a person has checked.",
            "splits": splits, "items": rows}


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
    for split, subsets in report["splits"].items():
        for subset, s in subsets.items():
            d, g, loc = s["detection"]["strict"], s["segmentation"], s["detection"]["localized"]
            lab = s["labels"]
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
    ev = sub.add_parser("evaluate")
    ev.add_argument("--work-dir", default="datasets/derived/cv_gold/eval")
    ev.add_argument("--out", default=str(REPORT_PATH))
    args = ap.parse_args(argv)

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
