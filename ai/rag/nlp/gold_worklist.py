"""Annotation worklist for the NLP gold set, its validator, and inter-annotator agreement (annotation-guidelines §4).

    python -m ai.rag.nlp.gold_worklist build             # write the worklist and its manifest (deterministic)
    python -m ai.rag.nlp.gold_worklist build --check     # fail if the committed worklist is not what the PDFs give today
    python -m ai.rag.nlp.gold_worklist validate FILE     # check a filled file (a copy of the worklist, or nlp_gold_v1.jsonl)
    python -m ai.rag.nlp.gold_worklist agreement A B     # token-level Cohen's kappa of two annotators on their shared cases

The worklist is **not** the gold set. It selects the pages to annotate and gives their exact text; every case has an empty
`annotations` list and an empty `annotator`. People fill them in a copy (one copy per annotator for the double-annotated
cases), `validate` checks the copy, and only then does it become `nlp_gold_v1.jsonl`. Nothing here proposes a span: §4.6
forbids pre-filling from the pipeline, and `validate` warns when a case's annotations are exactly what the extractors emit.

Selection (§4.4): pages are those `propose_candidates.indexed_pages` keeps (native text layer, not garbled) with at least
MIN_CHARS characters of indexed text, from the committed NTRS PDFs of sources the registry clears. Each document gets
PER_DOCUMENT pages (all it has, if fewer), the remaining cases go to the documents with the most eligible pages, and pages
are drawn with a seeded RNG. Splits are by **document** (no document in two splits), targeted at 50/25/25 of the cases, and
20 % of the cases, stratified by split, are marked for double annotation (§4.5). OCR-only pages are left out: OCR text
depends on the Tesseract version, so its offsets would not reproduce.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PDF_DIR = ROOT / "docs" / "research"
EVAL_DIR = ROOT / "datasets" / "evaluation"
WORKLIST = EVAL_DIR / "nlp_gold_v1_worklist.jsonl"
MANIFEST = EVAL_DIR / "nlp_gold_v1_worklist.manifest.json"
SCHEMA = EVAL_DIR / "nlp_gold_v1.schema.json"

SEED = 2026
TOTAL_CASES = 60
PER_DOCUMENT = 2
MIN_CHARS = 300
SPLIT_SHARES = {"dev": 0.50, "validation": 0.25, "holdout": 0.25}
DOUBLE_SHARE = 0.20
KAPPA_THRESHOLD = 0.65
RUBRIC_VERSION = "annotation-guidelines-0.3.4"
# The 14 entity types of docs/ai/nlp-pipeline.md §2 (annotation-guidelines §4.2).
LABELS = frozenset({
    "experiment", "investigation", "publication", "dataset", "phenomenon", "fuel", "oxidizer", "environmental_condition",
    "measurement", "instrument", "physical_quantity", "material", "research_finding", "hypothesis",
})
_AI_NAME = re.compile(r"claude|gpt|openai|anthropic|\bllm\b|\bai\b|assistant|\bbot\b", re.IGNORECASE)
_TOKEN = re.compile(r"\S+")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cleared_document_ids() -> set[str] | None:
    """NTRS documents whose registry source is cleared (verified and licensed); None if the registry cannot be read."""
    try:
        sys.path.insert(0, str(ROOT / "apps" / "api"))
        from flame_api.registry import read_registry, uncleared_sources
    except Exception:   # noqa: BLE001 - the worklist can be built without the API package
        return None
    blocked = uncleared_sources()
    return {row["source_id"] for row in read_registry() if row["source_id"] not in blocked}


def eligible_pages(pdf_dir: Path = PDF_DIR) -> dict[str, list[dict]]:
    """document_id -> [{page, chunk_text}] for every page the worklist may draw from."""
    from ai.rag.evaluation.propose_candidates import indexed_pages

    cleared = _cleared_document_ids()
    out: dict[str, list[dict]] = {}
    for path in sorted(Path(pdf_dir).glob("*.pdf")):
        document_id = f"FF-NTRS-{path.stem}"
        if cleared is not None and document_id not in cleared:
            continue
        out[document_id] = [{"page": p["page"], "chunk_text": p["indexed"]} for p in indexed_pages(path)
                            if len(p["indexed"]) >= MIN_CHARS]
    return out


def _quotas(available: dict[str, int], total: int, per_document: int) -> dict[str, int]:
    """per_document pages each (or all a document has); the rest one at a time, round-robin over the documents with the
    most eligible pages, so no single report dominates the set."""
    quota = {d: min(per_document, n) for d, n in available.items()}
    remaining = total - sum(quota.values())
    order = sorted(available, key=lambda d: (-available[d], d))
    while remaining > 0:
        progressed = False
        for document in order:
            if remaining and quota[document] < available[document]:
                quota[document] += 1
                remaining -= 1
                progressed = True
        if not progressed:
            break
    return quota


def _assign_splits(quota: dict[str, int], rng: random.Random) -> dict[str, str]:
    """Whole documents to splits, largest first (ties shuffled), each to the split furthest below its target share."""
    total = sum(quota.values())
    targets = {s: share * total for s, share in SPLIT_SHARES.items()}
    documents = [d for d in quota if quota[d]]
    rng.shuffle(documents)
    documents.sort(key=lambda d: -quota[d])
    filled = dict.fromkeys(SPLIT_SHARES, 0)
    split_of = {}
    for document in documents:
        split = min(SPLIT_SHARES, key=lambda s: ((filled[s] + quota[document]) / targets[s], s))
        split_of[document] = split
        filled[split] += quota[document]
    return split_of


def build(pdf_dir: Path = PDF_DIR) -> tuple[list[dict], dict]:
    pages = eligible_pages(pdf_dir)
    excluded = {d: "no page with a native, non-garbled text layer of at least "
                   f"{MIN_CHARS} characters (OCR-only or garbled; OCR text is not reproducible)" for d, p in pages.items() if not p}
    available = {d: len(p) for d, p in pages.items() if p}
    quota = _quotas(available, TOTAL_CASES, PER_DOCUMENT)
    rng = random.Random(SEED)
    split_of = _assign_splits(quota, rng)
    cases = []
    for document in sorted(quota):
        chosen = random.Random(f"{SEED}:{document}").sample(pages[document], quota[document])
        for page in sorted(chosen, key=lambda p: p["page"]):
            cases.append({"split": split_of[document], "document_id": document, "page": page["page"],
                          "chunk_text": page["chunk_text"]})
    for number, case in enumerate(cases, start=1):
        case["gold_id"] = f"NG-{number:03d}"
    double: list[str] = []
    for split in SPLIT_SHARES:
        ids = [c["gold_id"] for c in cases if c["split"] == split]
        double += random.Random(f"{SEED}:double:{split}").sample(ids, round(DOUBLE_SHARE * len(ids)))
    worklist = [{"gold_id": c["gold_id"], "split": c["split"], "document_id": c["document_id"], "page": c["page"],
                 "chunk_text": c["chunk_text"], "annotations": [], "annotator": "", "rubric_version": RUBRIC_VERSION}
                for c in cases]
    manifest = {
        "purpose": "NLP gold annotation worklist (annotation-guidelines §4). Not gold: annotations are empty until people fill them.",
        "built_by": "python -m ai.rag.nlp.gold_worklist build",
        "seed": SEED, "total_cases": len(cases), "per_document": PER_DOCUMENT, "min_chars": MIN_CHARS,
        "rubric_version": RUBRIC_VERSION, "labels": sorted(LABELS),
        "split_targets": SPLIT_SHARES,
        "split_counts": dict(Counter(c["split"] for c in cases)),
        "documents": {d: {"split": split_of[d], "cases": quota[d], "eligible_pages": available[d]} for d in sorted(quota)},
        "excluded_documents": excluded,
        "double_annotate": sorted(double),
        "kappa_threshold": KAPPA_THRESHOLD,
        "cases": {c["gold_id"]: {"document_id": c["document_id"], "page": c["page"], "split": c["split"],
                                 "chunk_sha256": _sha(c["chunk_text"])} for c in cases},
    }
    return worklist, manifest


def _dump_worklist(worklist: list[dict]) -> str:
    return "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in worklist)


def _dump_manifest(manifest: dict) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=1) + "\n"


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(cases: list[dict], manifest: dict, *, require_annotated: bool = True) -> tuple[list[str], list[str]]:
    """(problems, warnings) for a filled copy of the worklist. A problem means the file cannot become gold."""
    from jsonschema import Draft7Validator

    schema = Draft7Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    problems: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for line, case in enumerate(cases, start=1):
        label = case.get("gold_id") or f"line {line}"
        untouched = not (case.get("annotator") or "").strip() and not case.get("annotations")
        if untouched and not require_annotated:
            continue   # --partial: a case nobody has started yet is fine
        for error in schema.iter_errors(case):
            problems.append(f"{label}: {'/'.join(map(str, error.absolute_path)) or '(case)'}: {error.message}")
        if label in seen:
            problems.append(f"{label}: duplicate gold_id")
        seen.add(label)
        expected = manifest["cases"].get(label)
        if expected is None:
            problems.append(f"{label}: not in the worklist")
            continue
        for key in ("document_id", "page", "split"):
            if case.get(key) != expected[key]:
                problems.append(f"{label}: {key} is {case.get(key)!r}, the worklist says {expected[key]!r}")
        text = case.get("chunk_text", "")
        if _sha(text) != expected["chunk_sha256"]:
            problems.append(f"{label}: chunk_text differs from the worklist (annotate the text as given, never edit it)")
        annotator = (case.get("annotator") or "").strip()
        if _AI_NAME.search(annotator):
            problems.append(f"{label}: annotator {annotator!r} looks like an AI; gold annotations are made by people (§4.6)")
        spans = case.get("annotations") or []
        if require_annotated and not annotator:
            problems.append(f"{label}: no annotator")
        if require_annotated and annotator and not spans:
            warnings.append(f"{label}: annotated by {annotator} with no spans (fine only if the page truly names no entity)")
        keys = set()
        for index, span in enumerate(spans):
            where = f"{label}: annotation {index}"
            if span.get("record_type") not in LABELS:
                problems.append(f"{where}: record_type {span.get('record_type')!r} is not one of the 14 labels")
            start, end = span.get("char_start"), span.get("char_end")
            if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text)):
                problems.append(f"{where}: offsets {start}-{end} are outside the chunk")
            elif text[start:end] != span.get("text"):
                problems.append(f"{where}: text {span.get('text')!r} is not chunk_text[{start}:{end}] = {text[start:end]!r}")
            key = (span.get("record_type"), start, end)
            if key in keys:
                problems.append(f"{where}: duplicate span")
            keys.add(key)
        if spans and keys == _pipeline_spans(case):
            warnings.append(f"{label}: the annotations are exactly what the extractors emit; §4.6 forbids pre-filling from the pipeline")
    missing = sorted(set(manifest["cases"]) - seen - {c.get("gold_id") for c in cases})
    if require_annotated and missing:
        warnings.append(f"{len(missing)} worklist cases are not in this file yet: {', '.join(missing[:10])}{' ...' if len(missing) > 10 else ''}")
    return problems, warnings


def _pipeline_spans(case: dict) -> set[tuple]:
    """The (record_type, start, end) the default extractors emit for this chunk, restricted to the gold labels."""
    try:
        from ai.rag.nlp.pipeline import default_extractors, extract_chunk
        from ai.rag.nlp.records import ChunkInput
        from ai.rag.nlp.vocab import load_vocabulary
    except Exception:   # noqa: BLE001 - the warning is best-effort
        return set()
    chunk = ChunkInput(case["gold_id"], case["document_id"], "v1", case.get("page"), case["chunk_text"])
    records, _ = extract_chunk(chunk, default_extractors(load_vocabulary()))
    return {(r.record_type, r.char_start, r.char_end) for r in records if r.record_type in LABELS}


def _token_labels(case: dict) -> list[str]:
    """One label per whitespace token: the sorted set of annotation types covering any of its characters, or 'O'."""
    out = []
    for token in _TOKEN.finditer(case["chunk_text"]):
        types = sorted({a["record_type"] for a in case["annotations"]
                        if a["char_start"] < token.end() and a["char_end"] > token.start()})
        out.append("+".join(types) or "O")
    return out


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    if len(a) != len(b) or not a:
        raise ValueError("label sequences must be non-empty and the same length")
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    count_a, count_b = Counter(a), Counter(b)
    expected = sum(count_a[k] * count_b[k] for k in count_a.keys() | count_b.keys()) / (n * n)
    return None if expected == 1 else (observed - expected) / (1 - expected)


def agreement(first: list[dict], second: list[dict]) -> dict:
    """Token-level Cohen's kappa over the cases both files annotated (§4.5). Different annotators are required."""
    by_id = {c["gold_id"]: c for c in second}
    shared = [c for c in first if c["gold_id"] in by_id]
    same = [c["gold_id"] for c in shared if c.get("annotator", "").strip().lower() == by_id[c["gold_id"]].get("annotator", "").strip().lower()]
    if same:
        raise ValueError(f"agreement needs two different annotators; same annotator on {', '.join(same)}")
    a, b = [], []
    for case in shared:
        a += _token_labels(case)
        b += _token_labels(by_id[case["gold_id"]])
    kappa = cohen_kappa(a, b) if a else None
    return {"cases": [c["gold_id"] for c in shared], "tokens": len(a), "kappa": kappa,
            "threshold": KAPPA_THRESHOLD, "passes": kappa is not None and kappa >= KAPPA_THRESHOLD}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="write the worklist and manifest")
    b.add_argument("--check", action="store_true", help="fail if the committed files differ from a fresh build")
    v = sub.add_parser("validate", help="check a filled copy of the worklist")
    v.add_argument("file", type=Path)
    v.add_argument("--partial", action="store_true", help="allow cases that are not annotated yet")
    g = sub.add_parser("agreement", help="token-level Cohen's kappa of two annotators")
    g.add_argument("first", type=Path)
    g.add_argument("second", type=Path)
    args = parser.parse_args(argv)

    if args.command == "build":
        worklist, manifest = build()
        body, meta = _dump_worklist(worklist), _dump_manifest(manifest)
        if args.check:
            stale = [p.name for p, text in ((WORKLIST, body), (MANIFEST, meta)) if not p.exists() or p.read_text(encoding="utf-8") != text]
            if stale:
                print(f"stale: {', '.join(stale)}; rerun python -m ai.rag.nlp.gold_worklist build", file=sys.stderr)
                return 1
            print("worklist current")
            return 0
        WORKLIST.write_text(body, encoding="utf-8")
        MANIFEST.write_text(meta, encoding="utf-8")
        print(json.dumps({"cases": manifest["total_cases"], "documents": len(manifest["documents"]),
                          "split_counts": manifest["split_counts"], "double_annotate": len(manifest["double_annotate"]),
                          "excluded_documents": sorted(manifest["excluded_documents"])}, indent=1))
        return 0

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if args.command == "validate":
        problems, warnings = validate(load_cases(args.file), manifest, require_annotated=not args.partial)
        for warning in warnings:
            print(f"WARNING {warning}")
        for problem in problems:
            print(f"INVALID {problem}")
        print(f"{len(load_cases(args.file))} cases checked, {len(problems)} problems, {len(warnings)} warnings")
        return 1 if problems else 0
    result = agreement(load_cases(args.first), load_cases(args.second))
    print(json.dumps(result, indent=1))
    return 0 if result["passes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
