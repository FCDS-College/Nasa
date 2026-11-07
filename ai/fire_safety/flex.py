"""Canonical FLEX (PSI-69) features and outcome labels.

One definition shared by the training script (reads the committed CSV) and the API (reads ingested
``experiment_condition`` rows), so the model never sees features computed two different ways.
Variable names are the ingest slugs of the published headers (``flame_api.ingest._slug``).

Data-quality rules (docs/data/COMBUSTION_DATASET_ANALYSIS.md §3.1, §7):
* pressure <= 0 mmHg is physically impossible (test ``C11M201``) and treated as missing;
* the burning-rate column has an unresolved unit label and is an *outcome*, never a feature;
* burn time, extinction diameter and burning rate are measured after ignition, so they are
  excluded from the features to avoid leaking the outcome into the prediction.
"""
from __future__ import annotations

import csv
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

MMHG_PER_ATM = 760.0
KPA_PER_ATM = 101.325

# ingest slug -> canonical name
VARIABLES = {
    "ambient_pressure_mmhg": "pressure_mmhg",
    "o_initial_ambient_composition_mole_fraction": "o2",
    "n_initial_ambient_composition_mole_fraction": "n2",
    "co_initial_ambient_composition_mole_fraction": "co2",   # the published header lost its subscript: CO2, not CO
    "he_initial_ambient_composition_mole_fraction": "he",
    "droplet_initial_diameter_mm": "d0_mm",
    "visible_flame_extinction_diameter_mm": "extinction_diameter_mm",
    "burn_time_s": "burn_time_s",
    "test_end": "test_end",
    "test_date": "test_date",
    "flex_identifier": "flex_identifier",
    "fuel": "fuel",
}
OUTCOMES = ("Completion", "Disruption", "Extinction")   # sorted; the model's class order
FEATURES = ("o2", "pressure_atm", "ppo2_atm", "co2", "he", "d0_mm", "heptane")
FEATURE_LABELS = {
    "o2": "O₂ mole fraction",
    "pressure_atm": "ambient pressure (atm)",
    "ppo2_atm": "O₂ partial pressure (atm)",
    "co2": "CO₂ mole fraction (diluent)",
    "he": "He mole fraction (diluent)",
    "d0_mm": "initial droplet diameter (mm)",
    "heptane": "fuel is heptane (1) or methanol (0)",
}
FUELS = ("Methanol", "Heptane")
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
ROOT = Path(__file__).resolve().parents[2]
FLEX_TABLE = ROOT / "datasets" / "raw" / "psi_api" / "PSI-69" / "Experimental table" / "PSI-69_Experimental table_FLEX.csv"


def slug(header: str) -> str:
    """Identical to flame_api.ingest._slug."""
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_") or "value"


def number(raw: object) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    return float(text) if _NUMBER.fullmatch(text) else None


@dataclass(frozen=True)
class FlexTest:
    test_id: str
    test_date: str | None
    fuel: str | None
    features: dict[str, float] | None      # None when a required condition is missing or invalid
    outcome: str | None                   # Extinction | Disruption | Completion, or None
    raw: dict[str, object]                # canonical name -> value as published
    quality_flags: tuple[str, ...]


def features_from_values(values: Mapping[str, object], fuel: str | None) -> tuple[dict[str, float] | None, tuple[str, ...]]:
    """Model features from canonical values; (None, flags) if a required one is missing."""
    flags: list[str] = []
    o2 = number(values.get("o2"))
    pressure = number(values.get("pressure_mmhg"))
    d0 = number(values.get("d0_mm"))
    co2 = number(values.get("co2")) or 0.0
    he = number(values.get("he")) or 0.0
    if pressure is not None and pressure <= 0:
        flags.append("pressure_not_physical")
        pressure = None
    if fuel not in FUELS:
        flags.append("fuel_unknown")
    if o2 is None or pressure is None or d0 is None or fuel not in FUELS:
        flags.append("missing_required_condition")
        return None, tuple(flags)
    p_atm = pressure / MMHG_PER_ATM
    return {
        "o2": o2,
        "pressure_atm": p_atm,
        "ppo2_atm": o2 * p_atm,
        "co2": co2,
        "he": he,
        "d0_mm": d0,
        "heptane": 1.0 if fuel == "Heptane" else 0.0,
    }, tuple(flags)


def _from_canonical(test_id: str, values: dict[str, object]) -> FlexTest:
    fuel = (str(values.get("fuel") or "").strip() or None)
    features, flags = features_from_values(values, fuel)
    outcome = str(values.get("test_end") or "").strip()
    return FlexTest(
        test_id=test_id,
        test_date=(str(values.get("test_date") or "").strip() or None),
        fuel=fuel,
        features=features,
        outcome=outcome if outcome in OUTCOMES else None,
        raw=values,
        quality_flags=flags,
    )


def from_conditions(test_id: str, fuel: str | None, conditions: Mapping[str, tuple[float | None, str | None]]) -> FlexTest:
    """From ingested rows: {variable_slug: (value_numeric, value_text)}."""
    values: dict[str, object] = {}
    for variable, (numeric, text) in conditions.items():
        name = VARIABLES.get(variable)
        if name:
            values[name] = numeric if numeric is not None else text
    if fuel and "fuel" not in values:
        values["fuel"] = fuel
    return _from_canonical(test_id, values)


def load_table(path: Path = FLEX_TABLE) -> list[FlexTest]:
    """The committed FLEX table (Windows-1252, en dash = not available)."""
    with path.open("r", encoding="cp1252", newline="") as stream:
        rows = list(csv.DictReader(stream))
    tests = []
    for row in rows:
        values = {VARIABLES[slug(k)]: (v or "").strip() for k, v in row.items() if k and slug(k) in VARIABLES}
        tests.append(_from_canonical(values.get("flex_identifier") or "", values))
    return tests
