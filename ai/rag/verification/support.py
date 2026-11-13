"""Check that the figures an answer states can be traced to the evidence it cites (audit roadmap item 8).

This is a *traceability* check, not an entailment check. It finds numbers, quantities and identifiers in the answer
that appear nowhere in the cited passages (or the question), and names of concrete things (fuels, materials, oxidizers, instruments,
platforms: the controlled vocabulary of `ai/rag/nlp/vocab`) that the cited passages never mention under any alias. It cannot tell whether a supported number is used
correctly, and it says nothing about claims that contain no figure. It is deliberately conservative: it flags only
what it can show is missing, so a flag is a real signal and silence is not proof. A model-based claim checker
(NLI) can be added behind `ClaimChecker` once a passage-level gold set measures it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol, Sequence

from ai.rag.nlp.identifiers import IdentifierExtractor
from ai.rag.nlp.quantities import MeasurementExtractor
from ai.rag.nlp.records import ChunkInput
from ai.rag.nlp.vocab import VocabularyExtractor, load_vocabulary, vocabulary_version

CHECK_VERSION = "answer-support-1.1.0"
# Concrete things only: "ignition" or "pressure" are generic words a paraphrase can drop, a fuel or an instrument is not.
TERM_TYPES = ("fuel", "material", "oxidizer", "instrument", "platform")
UNIT_TOLERANCE = 0.01          # 1 %: "101.3 kPa" is "760 mmHg" (101.325 kPa) to the precision a sentence states
MIN_CHECKED_INTEGER = 11       # "two tests" and "3 samples" are counting words, not findings
_NUMBER = re.compile(r"(?<![\w.\-])\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?")
_SOURCE_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?")
_LIST_MARKER = re.compile(r"(?m)^[ \t]*(\d{1,3})[.)]")


@dataclass(frozen=True, slots=True)
class Unsupported:
    text: str
    kind: str          # "measurement" | "number" | "identifier"
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class SupportReport:
    checked: int
    unsupported: tuple[Unsupported, ...] = field(default_factory=tuple)
    version: str = CHECK_VERSION

    @property
    def supported(self) -> bool:
        return not self.unsupported

    @property
    def figures(self) -> tuple[Unsupported, ...]:
        """Unsupported numbers, quantities and identifiers: what `strict` mode may act on."""
        return tuple(u for u in self.unsupported if u.kind != "term")

    @property
    def terms(self) -> tuple[Unsupported, ...]:
        """Unsupported names of fuels, materials, oxidizers, instruments and platforms: a weaker signal, because a paraphrase can hide one."""
        return tuple(u for u in self.unsupported if u.kind == "term")


class ClaimChecker(Protocol):
    """Hook for a model-based check of claims that contain no figure. Not shipped: nothing measures one yet."""

    def unsupported_claims(self, answer: str, passages: Sequence[dict[str, str]]) -> list[str]: ...


@lru_cache(maxsize=1)
def _default_term_extractor() -> VocabularyExtractor:
    vocabulary = {t: entries for t, entries in load_vocabulary().items() if t in TERM_TYPES}
    return VocabularyExtractor(vocabulary, version=vocabulary_version(vocabulary))


def _value(text: str) -> float | None:
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def _close(a: float, b: float, tolerance: float = 1e-9) -> bool:
    return abs(a - b) <= tolerance * max(abs(a), abs(b), 1e-300)


def _chunk(text: str) -> ChunkInput:
    return ChunkInput("support", "support", "v1", None, text)


def _source_text(passages: Sequence[dict[str, str]], cited_ids: Sequence[str] | None) -> str:
    wanted = set(cited_ids or [])
    chosen = [p for p in passages if p["id"] in wanted] or list(passages)
    return "\n".join(p["text"] for p in chosen)


def _measurement_supported(payload: dict, sources: list[dict]) -> bool:
    value, value_si = payload["value"], payload["value_si"]
    for source in sources:
        if source["unit"] == payload["unit"] and _close(source["value"], value):
            return True
        if source["dimension"] != payload["dimension"]:
            continue
        low = source["value_si"]
        high = source["value_si_max"] if source["value_si_max"] is not None else low
        low, high = min(low, high), max(low, high)
        if low * (1 - UNIT_TOLERANCE) <= value_si <= high * (1 + UNIT_TOLERANCE) or (
                low < 0 and low * (1 + UNIT_TOLERANCE) <= value_si <= high * (1 - UNIT_TOLERANCE)):
            return True
    return False


def check_answer_support(answer: str, passages: Sequence[dict[str, str]], *, cited_ids: Sequence[str] | None = None,
                         question: str = "", term_extractor: VocabularyExtractor | None = None) -> SupportReport:
    """Every figure in `answer` should occur in the cited passages (all passages when none are cited) or in the question."""
    source = _source_text(passages, cited_ids) + "\n" + question
    source_measurements = [m.payload for m in MeasurementExtractor().extract(_chunk(source))]
    source_numbers = [v for token in _SOURCE_NUMBER.findall(source) if (v := _value(token)) is not None]
    lowered_source = source.lower()
    checked, unsupported = 0, []
    masked: list[tuple[int, int]] = []

    for record in MeasurementExtractor().extract(_chunk(answer)):
        masked.append((record.char_start, record.char_end))
        checked += 1
        raw_numbers = [v for v in (record.payload["value"], record.payload["value_max"]) if v is not None]
        if _measurement_supported(record.payload, source_measurements) or any(
                _close(raw, number) for raw in raw_numbers for number in source_numbers):
            continue
        unsupported.append(Unsupported(record.text, "measurement", record.char_start, record.char_end))

    for record in IdentifierExtractor().extract(_chunk(answer)):
        masked.append((record.char_start, record.char_end))
        checked += 1
        if record.text.lower() not in lowered_source and (record.normalized or "").lower() not in lowered_source:
            unsupported.append(Unsupported(record.text, "identifier", record.char_start, record.char_end))

    extractor = term_extractor or _default_term_extractor()
    known = {(r.record_type, r.normalized) for r in extractor.extract(_chunk(source))}
    for record in extractor.extract(_chunk(answer)):
        checked += 1
        if (record.record_type, record.normalized) not in known:
            unsupported.append(Unsupported(record.text, "term", record.char_start, record.char_end))

    markers = {m.start(1) for m in _LIST_MARKER.finditer(answer)}
    for match in _NUMBER.finditer(answer):
        if match.start() in markers or any(start <= match.start() < end for start, end in masked):
            continue
        token = match.group(0).rstrip(".,")
        value = _value(token)
        if value is None:
            continue
        if "." not in token and "e" not in token.lower() and "," not in token and value < MIN_CHECKED_INTEGER:
            continue
        checked += 1
        if not any(_close(value, number) for number in source_numbers):
            unsupported.append(Unsupported(token, "number", match.start(), match.end()))
    return SupportReport(checked, tuple(sorted(unsupported, key=lambda item: item.start)))
