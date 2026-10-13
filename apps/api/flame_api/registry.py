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


def validate_registry(path: Path = REGISTRY_CSV, schema_path: Path = REGISTRY_SCHEMA) -> list[str]:
    """Every problem as ``<source_id>: <field>: <message>``. Empty list means valid."""
    from jsonschema import Draft202012Validator, FormatChecker

    schema = load_schema(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    problems: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(read_registry(path, schema), start=2):
        label = row.get("source_id") or f"line {index}"
        for error in validator.iter_errors(row):
            field = "/".join(map(str, error.absolute_path)) or "(row)"
            problems.append(f"{label}: {field}: {error.message}")
        if row.get("source_id") in seen:
            problems.append(f"{label}: source_id: duplicate")
        seen.add(row.get("source_id"))
    return problems
