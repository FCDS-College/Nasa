"""Rule-based quantity extraction: a number (or range) followed by a known unit. Confidence 1.0, else dropped."""
from __future__ import annotations

import re

from ai.rag.nlp.records import ChunkInput, NlpRecord, span_record
from ai.rag.nlp.units import G_ACCELERATION, G_MASS, UNIT_TABLE_VERSION, UNITS

# A mantissa with optional thousands separators, then an optional exponent: 2e-3, 5 x 10^-3, 5 × 10^-3, 10^-6.
_NUM = r"[-+−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-+−]?\d+(?:\.\d+)?(?:\s?[eE][-+−]?\d+|\s?[x×]\s?10\^[-+−]?\d+|\^[-+−]?\d+)?"
_UNIT = "|".join(re.escape(u) for u in sorted(UNITS, key=len, reverse=True))
# Not after a word, decimal point, thousands comma, exponent caret or clock colon (OCR'd "23:30:3g.5"); not before
# letters, digits, a slash, a superscript or caret (an area "cm^2" is not a length).
_PATTERN = re.compile(rf"(?<![\w.,^:])(?P<lo>{_NUM})(?:\s*(?P<sep>–|—|-|to)\s*(?P<hi>{_NUM}))?\s?(?P<unit>{_UNIT})"
                      r"(?![A-Za-z/²³\d^])")
_GRAMS_OF = re.compile(r"\s+of\b")


def _number(text: str) -> float:
    text = text.replace("−", "-").replace(" ", "").replace(",", "")
    exponent = re.search(r"(?:[x×]10)?\^([-+]?\d+)$", text)
    if exponent is None:
        return float(text)
    mantissa = text[:exponent.start()]
    if exponent.group(0).startswith("^"):          # a bare power: 10^-6 is 1e-6
        return float(mantissa) ** int(exponent.group(1))
    return float(mantissa) * 10.0 ** int(exponent.group(1))


def _definition(unit: str, text: str, match: re.Match) -> tuple[str, float, float, str]:
    """The unit's (dimension, scale, offset, SI unit); a `g` is resolved from how it is written."""
    if unit == "g":
        if _GRAMS_OF.match(text, match.end()):
            return G_MASS                                       # "700 g of fuel"
        if match.start("unit") == match.end("lo") and match["hi"] is None:
            return G_ACCELERATION                               # "1g": gravity level, written against the number
    return UNITS[unit]


def _format(value_si: float, si_unit: str, value_si_max: float | None) -> str:
    unit = "" if si_unit == "1" else f" {si_unit}"
    if value_si_max is None:
        return f"{value_si:.6g}{unit}"
    return f"{value_si:.6g}–{value_si_max:.6g}{unit}"


class MeasurementExtractor:
    name = "measurement-rules"
    version = "1.1.0"
    method = "rule"

    def extract(self, chunk: ChunkInput) -> list[NlpRecord]:
        records = []
        for match in _PATTERN.finditer(chunk.text):
            unit = match["unit"]
            value, value_max = _number(match["lo"]), (_number(match["hi"]) if match["hi"] else None)
            if value_max is not None and value_max < value and match["sep"] == "-":
                continue        # "10-6 g": a superscript exponent (10⁻⁶) flattened by PDF text extraction, not a range
            dimension, scale, offset, si_unit = _definition(unit, chunk.text, match)
            value_si = value * scale + offset
            value_si_max = value_max * scale + offset if value_max is not None else None
            records.append(span_record(
                self, chunk, "measurement", match.start(), match.end(),
                normalized=_format(value_si, si_unit, value_si_max),
                payload={"value": value, "value_max": value_max, "unit": unit, "dimension": dimension,
                         "value_si": value_si, "value_si_max": value_si_max, "si_unit": si_unit,
                         "unit_table": UNIT_TABLE_VERSION}))
        return records
