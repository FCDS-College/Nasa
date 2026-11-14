"""Decode ``datasets/registry/source_registry.csv`` into schema-typed rows (M9, E2-1).

CSV encoding rules (documented in docs/data/SOURCE_REGISTRY.md):
* array fields are ``;``-separated (``video;digital stills``), trimmed, empty items dropped;
* an empty cell or the literal ``null`` means JSON null;
* ``known_file_count`` is an integer.
The same decoder feeds ``seed.py`` and ``knowledge/ingestion/validate_registry.py``, so what is
validated is exactly what is loaded.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_CSV = ROOT / "datasets" / "registry" / "source_registry.csv"
REGISTRY_SCHEMA = ROOT / "datasets" / "registry" / "source_registry.schema.json"
FILES_JSONL = ROOT / "datasets" / "metadata" / "files.jsonl"
NULL_TOKENS = frozenset({"", "null"})


def load_schema(path: Path = REGISTRY_SCHEMA) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _kinds(spec: dict[str, Any]) -> set[str]:
    kind = spec.get("type")
    return set(kind) if isinstance(kind, list) else {kind} if kind else set()


def decode_row(raw: dict[str, str], schema: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in raw.items():
        if key is None:
            continue
        text = (value or "").strip()
        spec = schema["properties"].get(key, {})
        kinds = _kinds(spec)
        if "array" in kinds:
            row[key] = [item.strip() for item in text.split(";") if item.strip()] if text.lower() not in NULL_TOKENS else []
        elif text.lower() in NULL_TOKENS:
            row[key] = None
        elif "integer" in kinds:
            try:
                row[key] = int(text.replace(",", ""))
            except ValueError:
                row[key] = text      # left as a string so validation reports it
        else:
            row[key] = text
    return row


def read_registry(path: Path = REGISTRY_CSV, schema: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    schema = schema or load_schema()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [decode_row(raw, schema) for raw in csv.DictReader(handle)]


# Uncleared sources that may keep committed files because nothing of theirs enters the knowledge base. Each needs its
# reason here and an open follow-up in docs/data/SOURCE_REGISTRY.md; `validate_registry.py` prints them as warnings.
KNOWN_UNCLEARED = {
    "FF-PSI-DSI": "non-combustion; excluded from ingestion (ingest.NOT_INGESTED_SOURCES), its frames are CV image assets; "
                  "licence not yet confirmed (PSI's study API returned 403 on 2026-11-14)",
}


def clearance_problem(row: dict[str, Any]) -> str | None:
    """Why a source may not enter the knowledge base yet, or None when it may (KB audit 2026-11-13).

    A source is cleared when its registry row is ``verified`` and records a licence. Anything less (partially verified,
    needs follow-up, no licence) is metadata only: it stays in the registry, but its files are not ingested or cited.
    """
    state = row.get("verification_state")
    if state != "verified":
        return f"verification_state is {state or 'missing'}, not verified"
    if not row.get("license"):
        return "no licence recorded"
    return None


def uncleared_sources(path: Path = REGISTRY_CSV) -> dict[str, str]:
    """source_id -> reason, for every source whose files must not be ingested."""
    return {row["source_id"]: problem for row in read_registry(path) if (problem := clearance_problem(row))}


def _sources_with_files(files_path: Path) -> set[str]:
    if not files_path.exists():
        return set()
    with files_path.open(encoding="utf-8") as handle:
        return {json.loads(line)["source_id"] for line in handle if line.strip()}


def validate_registry(path: Path = REGISTRY_CSV, schema_path: Path = REGISTRY_SCHEMA,
                      files_path: Path = FILES_JSONL) -> list[str]:
    """Every problem as ``<source_id>: <field>: <message>``. Empty list means valid.

    Besides the schema, a source that has files in ``files.jsonl`` must be cleared (verified and licensed), so
    unverified data cannot be added to the corpus without CI failing.
    """
    from jsonschema import Draft202012Validator, FormatChecker

    schema = load_schema(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    problems: list[str] = []
    seen: set[str] = set()
    with_files = _sources_with_files(files_path)
    for index, row in enumerate(read_registry(path, schema), start=2):
        label = row.get("source_id") or f"line {index}"
        for error in validator.iter_errors(row):
            field = "/".join(map(str, error.absolute_path)) or "(row)"
            problems.append(f"{label}: {field}: {error.message}")
        if row.get("source_id") in seen:
            problems.append(f"{label}: source_id: duplicate")
        seen.add(row.get("source_id"))
        if row.get("source_id") in with_files and row.get("source_id") not in KNOWN_UNCLEARED \
                and (reason := clearance_problem(row)):
            field = "license" if reason == "no licence recorded" else "verification_state"
            problems.append(f"{label}: {field}: has committed files but is not cleared for ingestion "
                            f"({reason.split(',')[0]})")
    return problems


def clearance_warnings(path: Path = REGISTRY_CSV, files_path: Path = FILES_JSONL) -> list[str]:
    """The KNOWN_UNCLEARED sources that still have files: allowed, but reported so the follow-up is not forgotten."""
    blocked, with_files = uncleared_sources(path), _sources_with_files(files_path)
    return [f"{sid}: {blocked[sid]}; {why}" for sid, why in KNOWN_UNCLEARED.items() if sid in blocked and sid in with_files]
