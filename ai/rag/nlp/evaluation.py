"""Gold-set loading and span-level scoring for the D1 extractors (docs/evaluation/annotation-guidelines.md §4)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ai.rag.nlp.records import NlpRecord


@dataclass(frozen=True)
class GoldCase:
    gold_id: str
    split: str
    document_id: str
    page: int | None
    chunk_text: str
    annotations: list[dict]


def load_gold(path: str | Path, *, split: str | None = None) -> list[GoldCase]:
    cases = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if split is None or raw["split"] == split:
            cases.append(GoldCase(raw["gold_id"], raw["split"], raw["document_id"], raw.get("page"), raw["chunk_text"],
                                  raw["annotations"]))
    return cases


def gold_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    overlap = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - overlap
    return overlap / union if union else 0.0


def _matches(gold: dict, record: NlpRecord, relaxed: bool) -> bool:
    if gold["record_type"] != record.record_type:
        return False
    span_g, span_p = (gold["char_start"], gold["char_end"]), (record.char_start, record.char_end)
    return _iou(span_g, span_p) >= 0.5 if relaxed else span_g == span_p


def score(cases: list[GoldCase], predictions: dict[str, list[NlpRecord]], *, relaxed: bool = False) -> dict[str, dict]:
    """Per-type tp/fp/fn and precision/recall/f1. A zero denominator gives None, never a made-up 0.0."""
    counts: dict[str, dict[str, int]] = {}

    def bucket(record_type: str) -> dict[str, int]:
        return counts.setdefault(record_type, {"tp": 0, "fp": 0, "fn": 0})

    for case in cases:
        remaining = list(predictions.get(case.gold_id, []))
        for gold in case.annotations:
            hit = next((p for p in remaining if _matches(gold, p, relaxed)), None)
            if hit is None:
                bucket(gold["record_type"])["fn"] += 1
            else:
                remaining.remove(hit)
                bucket(gold["record_type"])["tp"] += 1
        for extra in remaining:
            bucket(extra.record_type)["fp"] += 1
    out = {}
    for record_type, c in counts.items():
        precision = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else None
        recall = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else None
        if precision is None or recall is None:
            f1 = None
        else:
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[record_type] = {**c, "precision": precision, "recall": recall, "f1": f1}
    return out
