"""Rule-based quantity extraction: a number (or range) followed by a known unit. Confidence 1.0, else dropped."""
from __future__ import annotations

import re

from ai.rag.nlp.records import ChunkInput, NlpRecord, span_record
from ai.rag.nlp.units import UNIT_TABLE_VERSION, UNITS, to_si

_NUM = r"[-+−]?\d+(?:\.\d+)?(?:\s?[eE][-+]?\d+)?"
_UNIT = "|".join(re.escape(u) for u in sorted(UNITS, key=len, reverse=True))
_PATTERN = re.compile(rf"(?<![\w.])(?P<lo>{_NUM})(?:\s*(?:–|—|-|to)\s*(?P<hi>{_NUM}))?\s?(?P<unit>{_UNIT})(?![A-Za-z/²³\d])")


def _number(text: str) -> float:
    return float(text.replace("−", "-").replace(" ", ""))


def _format(value_si: float, si_unit: str, value_si_max: float | None) -> str:
    unit = "" if si_unit == "1" else f" {si_unit}"
    if value_si_max is None:
        return f"{value_si:.6g}{unit}"
    return f"{value_si:.6g}–{value_si_max:.6g}{unit}"


class MeasurementExtractor:
    name = "measurement-rules"
    version = "1.0.0"
    method = "rule"

    def extract(self, chunk: ChunkInput) -> list[NlpRecord]:
        records = []
        for match in _PATTERN.finditer(chunk.text):
            unit = match["unit"]
            value, value_max = _number(match["lo"]), (_number(match["hi"]) if match["hi"] else None)
            value_si, si_unit = to_si(value, unit)
            value_si_max = to_si(value_max, unit)[0] if value_max is not None else None
            records.append(span_record(
                self, chunk, "measurement", match.start(), match.end(),
                normalized=_format(value_si, si_unit, value_si_max),
                payload={"value": value, "value_max": value_max, "unit": unit, "dimension": UNITS[unit][0],
                         "value_si": value_si, "value_si_max": value_si_max, "si_unit": si_unit,
                         "unit_table": UNIT_TABLE_VERSION}))
        return records
