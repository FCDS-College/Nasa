"""Controlled-vocabulary lookup, terminology normalisation, measurement linking and condition promotion."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from ai.rag.nlp.records import ChunkInput, NlpRecord, span_record

VOCAB_DIR = Path(__file__).parent / "vocab"
MIN_ALIAS_CHARS = 3
# Quantities whose measurements describe the experiment's conditions (proposal; reviewed with the seed vocabularies).
CONDITION_DIMENSIONS = frozenset({"pressure", "temperature"})
CONDITION_QUANTITIES = frozenset({"oxygen concentration", "pressure", "ambient pressure", "temperature", "flow velocity"})
_FILLER = re.compile(r"^[\s:=,]*(?:(?:was|is|of|at|to|about|approximately|~)\s+)*$", re.IGNORECASE)
_MAX_LINK_GAP = 40


def _alias_parts(alias: str | dict) -> tuple[str, bool]:
    if isinstance(alias, dict):
        return alias["text"], bool(alias.get("case_sensitive"))
    if len(alias) < MIN_ALIAS_CHARS:
        raise ValueError(f"alias {alias!r} is shorter than {MIN_ALIAS_CHARS} characters; make it case-sensitive")
    return alias, False


def vocabulary_version(vocabulary: dict) -> str:
    return "vocab-" + hashlib.sha256(json.dumps(vocabulary, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:8]


def load_vocabulary(extra: dict[str, dict[str, list]] | None = None) -> dict[str, dict[str, list]]:
    """Seed files merged with `extra` (e.g. names read from the knowledge graph). Extra never overrides a seed canonical."""
    vocabulary = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(VOCAB_DIR.glob("*.json"))}
    for record_type, entries in (extra or {}).items():
        target = vocabulary.setdefault(record_type, {})
        for canonical, aliases in entries.items():
            known = {a if isinstance(a, str) else a["text"] for a in target.get(canonical, [])}
            target.setdefault(canonical, [])
            target[canonical].extend(a for a in aliases if (a if isinstance(a, str) else a["text"]) not in known)
    return vocabulary


class VocabularyExtractor:
    name = "vocabulary-lookup"
    method = "rule"

    def __init__(self, vocabulary: dict[str, dict[str, list]], version: str) -> None:
        self.version = version
        self._groups: list[tuple[str, bool, re.Pattern, dict[str, str]]] = []
        for record_type, entries in vocabulary.items():
            for case_sensitive in (False, True):
                lookup: dict[str, str] = {}
                for canonical, aliases in entries.items():
                    parts = [_alias_parts(alias) for alias in aliases]
                    # The canonical name is matched case-insensitively unless the entry spells it out as a case-sensitive
                    # alias: an acronym such as SAME or FLEX is also an ordinary word in lower case.
                    explicit = {text.lower() for text, sensitive in parts if sensitive}
                    lookup_entries = ([] if canonical.lower() in explicit else [(canonical, False)]) + parts
                    for text, sensitive in lookup_entries:
                        if sensitive == case_sensitive:
                            lookup[text if case_sensitive else text.lower()] = canonical
                if lookup:
                    alternatives = "|".join(re.escape(t) for t in sorted(lookup, key=len, reverse=True))
                    flags = 0 if case_sensitive else re.IGNORECASE
                    pattern = re.compile(rf"(?<![A-Za-z0-9])(?:{alternatives})(?![A-Za-z0-9])", flags)
                    self._groups.append((record_type, case_sensitive, pattern, lookup))

    def extract(self, chunk: ChunkInput) -> list[NlpRecord]:
        records = []
        for record_type, case_sensitive, pattern, lookup in self._groups:
            for match in pattern.finditer(chunk.text):
                key = match.group(0) if case_sensitive else match.group(0).lower()
                records.append(span_record(self, chunk, record_type, match.start(), match.end(), normalized=lookup[key]))
        return sorted(records, key=lambda r: (r.char_start, r.record_type))


def link_measurements(chunk: ChunkInput, records: list[NlpRecord]) -> list[NlpRecord]:
    """Add `payload["quantity"]` to a measurement when a physical quantity ends shortly before it with only filler between."""
    quantities = [r for r in records if r.record_type == "physical_quantity"]
    linked = []
    for record in records:
        if record.record_type == "measurement":
            candidates = [q for q in quantities if q.char_end <= record.char_start
                          and record.char_start - q.char_end <= _MAX_LINK_GAP]
            nearest = max(candidates, key=lambda q: q.char_end, default=None)
            if nearest is not None and _FILLER.match(chunk.text[nearest.char_end:record.char_start]):
                record = record.model_copy(update={"payload": {**record.payload, "quantity": nearest.normalized}})
        linked.append(record)
    return linked


def promote_conditions(records: list[NlpRecord]) -> list[NlpRecord]:
    """Extra `environmental_condition` records (same span) for condition-like measurements."""
    promoted = []
    for record in records:
        if record.record_type == "measurement" and (
            record.payload.get("dimension") in CONDITION_DIMENSIONS or record.payload.get("quantity") in CONDITION_QUANTITIES
        ):
            promoted.append(record.model_copy(update={"record_type": "environmental_condition", "extractor": "condition-rules",
                                                      "extractor_version": "1.0.0"}))
    return promoted
