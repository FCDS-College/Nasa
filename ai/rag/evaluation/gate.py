"""One command that checks every release-gate row (docs/evaluation/release-gate.md) against the latest measurements.

    python -m ai.rag.evaluation.gate --run-offline                       # run the offline exams, then judge every row
    python -m ai.rag.evaluation.gate --baseline docs/evaluation/baselines/gate_baseline.json     # also fail on a regression
    python -m ai.rag.evaluation.gate --enforce                           # exit 1 when any row FAILS
    python -m ai.rag.evaluation.gate --release                           # exit 1 unless every row PASSES with verified labels

Each row of `gate_config.json` names a report file, where the value (and its 95 % interval) sits in it, and a threshold. A row is
one of four states, and a row with no report is never silently green:

* PASS          the threshold is met (with `decision: ci`, even the interval's worse end meets it);
* FAIL          the threshold is missed (with `decision: ci`, even the interval's better end misses it);
* INCONCLUSIVE  the interval straddles the threshold (the sample is too small to say), no interval is available, or the labels are
                not yet verified (release mode);
* NOT_MEASURED  there is no report for this row, so nothing is claimed.

Exit codes: 1 on a regression against `--baseline` (a drop of more than 0.02, absolute, on any measured row), always; 1 on a FAIL with
`--enforce`; 1 on anything but PASS with `--release`. Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CONFIG = Path(__file__).with_name("gate_config.json")
DEFAULT_REPORTS_DIR = ROOT / "docs" / "evaluation" / "reports" / "latest"
REGRESSION_TOLERANCE = 0.02

PASS, FAIL, INCONCLUSIVE, NOT_MEASURED = "PASS", "FAIL", "INCONCLUSIVE", "NOT_MEASURED"


def dig(data: Any, path: str) -> Any:
    """Follow a dotted path through nested dicts (`splits.holdout.all.segmentation.meanIoU`); None if any step is missing."""
    node = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def decide(value: float, direction: str, threshold: float, ci: tuple[float, float] | None, decision: str) -> str:
    """PASS / FAIL / INCONCLUSIVE for one measured value. `direction` is `min` (higher is better) or `max` (lower is better)."""
    if decision == "ci":
        if ci is None or None in ci:
            return INCONCLUSIVE      # a threshold on a sample cannot be judged without its interval
        low, high = ci
        if direction == "min":
            return PASS if low >= threshold else FAIL if high < threshold else INCONCLUSIVE
        return PASS if high <= threshold else FAIL if low > threshold else INCONCLUSIVE
    return PASS if (value >= threshold if direction == "min" else value <= threshold) else FAIL


def read_metric_report(row: dict, reports_dir: Path) -> dict:
    """Value, interval, sample size and verified count for a `metric_report` row; `state: NOT_MEASURED` when the report is absent."""
    source = row["source"]
    path = Path(source["path"].replace("{reports_dir}", str(reports_dir)))
    path = path if path.is_absolute() else ROOT / path
    if not path.exists():
        return {"state": NOT_MEASURED, "note": f"no report at {_display(path)}"}
    data = json.loads(path.read_text(encoding="utf-8"))
    value = dig(data, source["value"])
    if not isinstance(value, (int, float)):
        return {"state": NOT_MEASURED, "note": f"{_display(path)} has no number at `{source['value']}`"}
    ci = dig(data, source["ci"]) if source.get("ci") else None
    if ci is None and source.get("per_question"):
        # Older benchmark reports carry no interval: derive it from the per-question scores (same bootstrap as the benchmark).
        from ai.rag.evaluation.stats import bootstrap_ci
        scores = [q[source["per_question"]] for q in data.get("per_question", []) if source["per_question"] in q]
        ci = list(bootstrap_ci(scores)) if scores else None
    verified = dig(data, source["verified"]) if source.get("verified") else None
    return {"state": "MEASURED", "value": float(value), "ci": tuple(ci) if ci else None,
            "n": dig(data, source["n"]) if source.get("n") else None,
            "verified": verified, "report": _display(path)}


def read_junit(row: dict, junit_path: Path | None) -> dict:
    """Pass rate of the tests whose class name contains one of the row's fragments. Skipped tests make the row NOT_MEASURED."""
    if junit_path is None or not junit_path.exists():
        return {"state": NOT_MEASURED, "note": "no JUnit file: run pytest with --junitxml and pass --junit"}
    fragments = row["source"]["classname_contains"]
    ran = failed = skipped = 0
    for case in ET.parse(junit_path).getroot().iter("testcase"):
        if not any(fragment in case.get("classname", "") for fragment in fragments):
            continue
        ran += 1
        failed += case.find("failure") is not None or case.find("error") is not None
        skipped += case.find("skipped") is not None
    if ran == 0:
        return {"state": NOT_MEASURED, "note": f"no test matching {fragments} in {junit_path.name}"}
    if skipped:
        return {"state": NOT_MEASURED, "note": f"{skipped} of {ran} contract tests were skipped"}
    return {"state": "MEASURED", "value": (ran - failed) / ran, "ci": None, "n": ran, "verified": ran, "report": junit_path.name}


def evaluate(config: dict, reports_dir: Path, junit_path: Path | None = None, baseline: dict | None = None, *, release: bool = False) -> list[dict]:
    rows = []
    for row in config["rows"]:
        kind = row["source"]["kind"]
        reading = read_junit(row, junit_path) if kind == "junit" else read_metric_report(row, reports_dir)
        out: dict[str, Any] = {"id": row["id"], "title": row["title"], "direction": row["direction"], "threshold": row["threshold"],
                               "caveat": row.get("caveat", ""), "informational": bool(row.get("informational"))}
        if reading["state"] != "MEASURED":
            out.update(status=NOT_MEASURED, note=reading["note"])
            rows.append(out)
            continue
        status = decide(reading["value"], row["direction"], row["threshold"], reading["ci"], row.get("decision", "point"))
        note = ""
        if reading["verified"] is not None and reading["verified"] == 0:
            note = "labels not verified by a person"
            if release and status == PASS:
                status = INCONCLUSIVE
        out.update(status=status, value=round(reading["value"], 4), ci95=None if reading["ci"] is None else [round(x, 4) for x in reading["ci"]],
                   n=reading["n"], report=reading["report"], note=note)
        if baseline and row["id"] in baseline:
            delta = reading["value"] - baseline[row["id"]]
            worse = -delta if row["direction"] == "min" else delta
            out["baseline"] = baseline[row["id"]]
            out["regression"] = bool(worse > REGRESSION_TOLERANCE + 1e-9)
        rows.append(out)
    return rows


def exit_code(rows: list[dict], *, enforce: bool, release: bool) -> int:
    """Informational rows (a proposed threshold nobody has signed off yet) are shown but never decide the exit code."""
    binding = [r for r in rows if not r.get("informational")]
    if any(r.get("regression") for r in binding):
        return 1
    if release:
        return int(any(r["status"] != PASS for r in binding))
    return int(enforce and any(r["status"] == FAIL for r in binding))


def render(rows: list[dict]) -> str:
    sign = {"min": "at least", "max": "at most"}
    lines = ["| Row | Measured | Required | Status | Note |", "|---|---|---|---|---|"]
    for r in rows:
        if r["status"] == NOT_MEASURED:
            measured = "n/a"
        else:
            measured = f"{r['value']:.4g}"
            if r.get("ci95"):
                measured += f" [{r['ci95'][0]:.3g}, {r['ci95'][1]:.3g}]"
            if r.get("n") is not None:
                measured += f", n={r['n']}"
        note = "; ".join(x for x in (r.get("note"), "REGRESSION vs baseline " + str(r["baseline"]) if r.get("regression") else "",
                                     "informational: threshold not signed off" if r.get("informational") else "", r.get("caveat")) if x)
        lines.append(f"| {r['title']} | {measured} | {sign[r['direction']]} {r['threshold']} | **{r['status']}** | {note} |")
    return "\n".join(lines)


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or None
    except OSError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR, help="where the offline exams write and the gate reads `{reports_dir}` files")
    parser.add_argument("--run-offline", action="store_true", help="run the offline exams (PII) into --reports-dir first")
    parser.add_argument("--junit", type=Path, help="pytest --junitxml output, for the API contract row")
    parser.add_argument("--baseline", type=Path, help="JSON {row_id: value}; a drop of more than 0.02 on any row is a regression")
    parser.add_argument("--write-baseline", type=Path, help="write the measured values as a new baseline file")
    parser.add_argument("--json", type=Path, help="write the full result as JSON")
    parser.add_argument("--md", type=Path, help="append the table as Markdown (use $GITHUB_STEP_SUMMARY in CI)")
    parser.add_argument("--enforce", action="store_true", help="exit 1 when any row FAILS")
    parser.add_argument("--release", action="store_true", help="exit 1 unless every row PASSES with verified labels (implies --enforce)")
    args = parser.parse_args(argv)

    config_text = args.config.read_text(encoding="utf-8")
    config = json.loads(config_text)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    if args.run_offline:
        from ai.rag.evaluation import run_pii_exam
        run_pii_exam.main(["--out", str(args.reports_dir / "pii-exam.json")])
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline and args.baseline.exists() else None
    rows = evaluate(config, args.reports_dir, args.junit, baseline, release=args.release)
    table = render(rows)
    print(table)

    code = exit_code(rows, enforce=args.enforce, release=args.release)
    counts = {s: sum(r["status"] == s for r in rows) for s in (PASS, FAIL, INCONCLUSIVE, NOT_MEASURED)}
    print(f"\nGate: {counts[PASS]} PASS, {counts[FAIL]} FAIL, {counts[INCONCLUSIVE]} INCONCLUSIVE, {counts[NOT_MEASURED]} NOT_MEASURED."
          f" Regressions: {sum(bool(r.get('regression')) for r in rows)}. Exit code {code}.")
    if args.json:
        args.json.write_text(json.dumps({"gate_version": config["version"], "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                         "git_commit": _git_commit(), "config_sha256": hashlib.sha256(config_text.encode()).hexdigest(),
                                         "counts": counts, "exit_code": code, "rows": rows}, indent=2) + "\n", encoding="utf-8")
    if args.md:
        with args.md.open("a", encoding="utf-8") as handle:
            handle.write("## Evaluation gate\n\n" + table + f"\n\n{counts[PASS]} PASS, {counts[FAIL]} FAIL, {counts[INCONCLUSIVE]} INCONCLUSIVE, {counts[NOT_MEASURED]} NOT_MEASURED.\n")
    if args.write_baseline:
        args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
        args.write_baseline.write_text(json.dumps({r["id"]: r["value"] for r in rows if "value" in r}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
