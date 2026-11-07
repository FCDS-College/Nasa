"""Summaries, comparison, scenario ranking and fire-safety insights across NASA investigations.

Pure functions over plain data (the API loads the rows; tests pass fixtures). Nothing here is
generated text: every number is computed from ingested flight-test rows, and every statement carries
the evidence IDs of the rows it was computed from. Free-text summaries come verbatim from NASA's
ISA-Tab metadata and are cited to their own evidence rows.

Ranking answers one question: **how directly does each investigation's flight data speak to a given
cabin atmosphere?** It is an evidence-relevance score, not a risk score, and its formula is returned
with every result:

    relevance = 0.35*oxygen_match + 0.25*pressure_match + 0.25*evidence_density + 0.15*outcome_data

* oxygen_match    1 if the scenario O2 is inside the tested O2 range, else exp(-gap/0.05); 0 if O2 not recorded
* pressure_match  1 if inside the tested pressure range, else exp(-|ln(P/P_nearest)|/0.25); 0 if not recorded
* evidence_density  min(1, ln(1+n)/ln(31)), n = tests within +/-0.03 O2 (and +/-25% pressure when recorded)
* outcome_data    1 if each test records its end state, 0.5 if only a duration is recorded, 0 if none
"""
from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from ai.fire_safety import flex
from ai.fire_safety.scenarios import Scenario

WEIGHTS = {"oxygen_match": 0.35, "pressure_match": 0.25, "evidence_density": 0.25, "outcome_data": 0.15}
O2_NEIGHBOURHOOD = 0.03
PRESSURE_NEIGHBOURHOOD = 1.25          # ratio
KPA_PER_MMHG = 0.133322387415
FORMULA = ("relevance = 0.35*oxygen_match + 0.25*pressure_match + 0.25*evidence_density + 0.15*outcome_data; "
           "oxygen_match = 1 inside the tested O2 range else exp(-gap/0.05); pressure_match = 1 inside the tested "
           "pressure range else exp(-|ln(P/P_nearest)|/0.25); evidence_density = min(1, ln(1+n)/ln(31)) for n tests "
           "within +/-0.03 O2 (and +/-25% pressure when recorded); outcome_data = 1 end state recorded, 0.5 duration only, "
           "0 none; unrecorded variables score 0 and are listed in 'not_recorded'.")


@dataclass
class Condition:
    numeric: float | None
    text: str | None
    si: float | None
    evidence_id: str


@dataclass
class TestRow:
    source_id: str
    experiment_id: str
    test_id: str
    fuel: str | None
    conditions: dict[str, Condition]


@dataclass
class Canonical:
    """The comparable view of one flight test. None means 'not recorded in the published table'."""
    row: TestRow
    o2: float | None = None
    o2_approximate: bool = False
    pressure_kpa: float | None = None
    flow_m_s: float | None = None
    material: str | None = None
    end_state: str | None = None
    duration_s: float | None = None
    flags: list[str] = field(default_factory=list)

    def evidence(self, variable: str) -> str | None:
        c = self.row.conditions.get(variable)
        return c.evidence_id if c else None


def _num(row: TestRow, variable: str) -> float | None:
    c = row.conditions.get(variable)
    return None if c is None else c.numeric


def _text(row: TestRow, variable: str) -> str | None:
    c = row.conditions.get(variable)
    return None if c is None else (c.text or (None if c.numeric is None else str(c.numeric)))


def _parse_percent_text(text: str | None) -> tuple[float | None, bool]:
    """SAFFIRE-I writes O2 as '21.5-21.7' or '~ 21.5' -> (fraction, approximate)."""
    if not text:
        return None, False
    values = [float(v) for v in re.findall(r"\d+(?:\.\d+)?", text)]
    if not values:
        return None, False
    return round(sum(values) / len(values) / 100, 5), True


def canonical(row: TestRow) -> Canonical:
    c = Canonical(row=row, material=row.fuel)
    sid = row.source_id
    if sid == "FF-PSI-69":                                   # FLEX droplets
        c.o2 = _num(row, "o_initial_ambient_composition_mole_fraction")
        mmhg = _num(row, "ambient_pressure_mmhg")
        if mmhg is not None and mmhg <= 0:
            c.flags.append("pressure_not_physical")
        elif mmhg is not None:
            c.pressure_kpa = mmhg * KPA_PER_MMHG
        end = _text(row, "test_end")
        c.end_state = end if end in flex.OUTCOMES else None
        c.duration_s = _num(row, "burn_time_s")
    elif sid == "FF-PSI-25":                                 # BASS-II solids
        pct = _num(row, "calibrated_initial_o2_by_vol")
        c.o2 = None if pct is None else pct / 100
    elif sid == "FF-PSI-98":                                 # SAFFIRE-I large-scale fabric
        c.o2, c.o2_approximate = _parse_percent_text(_text(row, "percent_o2"))
        flow = row.conditions.get("air_flow_cm_s")
        c.flow_m_s = flow.si if flow else None
        c.duration_s = _num(row, "burn_time_s")
    elif sid == "FF-PSI-107":                                # SPICE gaseous co-flow
        flow = row.conditions.get("air_rate_cm_s")
        if flow and flow.si is not None:
            if flow.si < 0:
                c.flags.append("negative_air_rate_sensor_offset")
            else:
                c.flow_m_s = flow.si
    return c


def _range(values: Iterable[float | None]) -> dict | None:
    v = [x for x in values if x is not None]
    if not v:
        return None
    return {"min": round(min(v), 6), "max": round(max(v), 6), "n": len(v)}


def envelope(tests: list[Canonical]) -> dict:
    """What an investigation's published table actually covers."""
    fuels = Counter((t.material or "not recorded") for t in tests)
    ends = Counter(t.end_state for t in tests if t.end_state)
    return {
        "tests": len(tests),
        "o2_fraction": _range(t.o2 for t in tests),
        "o2_approximate": any(t.o2_approximate for t in tests),
        "pressure_kpa": _range(t.pressure_kpa for t in tests),
        "flow_velocity_m_s": _range(t.flow_m_s for t in tests),
        "fuels_or_materials": [{"name": k, "tests": n} for k, n in fuels.most_common(12)],
        "distinct_fuels_or_materials": len(fuels),
        "end_states": dict(sorted(ends.items())) or None,
        "end_state_recorded": bool(ends),
        "duration_recorded": any(t.duration_s is not None for t in tests),
        "quality_flags": dict(Counter(f for t in tests for f in t.flags)),
    }


def _match_linear(value: float, rng: dict | None, scale: float) -> float:
    if rng is None:
        return 0.0
    if rng["min"] <= value <= rng["max"]:
        return 1.0
    gap = rng["min"] - value if value < rng["min"] else value - rng["max"]
    return math.exp(-gap / scale)


def _match_log(value: float, rng: dict | None, scale: float) -> float:
    if rng is None:
        return 0.0
    if rng["min"] <= value <= rng["max"]:
        return 1.0
    nearest = rng["min"] if value < rng["min"] else rng["max"]
    return math.exp(-abs(math.log(value / nearest)) / scale)


def neighbours(tests: list[Canonical], scenario: Scenario) -> list[Canonical]:
    # When an investigation records pressure, a test without a valid pressure (e.g. FLEX C11M201, 0 mmHg) cannot
    # be shown to lie within +/-25% of the scenario, so it is not a neighbour.
    pressure_recorded = any(t.pressure_kpa is not None for t in tests)
    out = []
    for t in tests:
        if t.o2 is None or abs(t.o2 - scenario.o2_fraction) > O2_NEIGHBOURHOOD:
            continue
        if pressure_recorded and t.pressure_kpa is None:
            continue
        if t.pressure_kpa is not None:
            ratio = t.pressure_kpa / scenario.pressure_kpa
            if not (1 / PRESSURE_NEIGHBOURHOOD <= ratio <= PRESSURE_NEIGHBOURHOOD):
                continue
        out.append(t)
    return out


def relevance(tests: list[Canonical], env: dict, scenario: Scenario) -> dict:
    near = neighbours(tests, scenario)
    components = {
        "oxygen_match": _match_linear(scenario.o2_fraction, env["o2_fraction"], 0.05),
        "pressure_match": _match_log(scenario.pressure_kpa, env["pressure_kpa"], 0.25),
        "evidence_density": min(1.0, math.log1p(len(near)) / math.log1p(30)),
        "outcome_data": 1.0 if env["end_state_recorded"] else 0.5 if env["duration_recorded"] else 0.0,
    }
    score = sum(WEIGHTS[k] * v for k, v in components.items())
    not_recorded = [name for name, key in (("O₂", "o2_fraction"), ("pressure", "pressure_kpa")) if env[key] is None]
    explanation = []
    if env["o2_fraction"] is None:
        explanation.append("O₂ is not recorded in this table")
    elif components["oxygen_match"] == 1:
        explanation.append(f"scenario O₂ {scenario.o2_fraction:.2f} is inside the tested range "
                           f"{env['o2_fraction']['min']:.3f}–{env['o2_fraction']['max']:.3f}")
    else:
        explanation.append(f"scenario O₂ {scenario.o2_fraction:.2f} is outside the tested range "
                           f"{env['o2_fraction']['min']:.3f}–{env['o2_fraction']['max']:.3f}")
    if env["pressure_kpa"] is None:
        explanation.append("pressure is not recorded in this table")
    else:
        inside = components["pressure_match"] == 1
        explanation.append(f"scenario pressure {scenario.pressure_kpa:.1f} kPa is {'inside' if inside else 'outside'} the tested range "
                           f"{env['pressure_kpa']['min']:.1f}–{env['pressure_kpa']['max']:.1f} kPa")
    explanation.append(f"{len(near)} flight test(s) within ±0.03 O₂"
                       + (" and ±25% pressure" if env["pressure_kpa"] else "") + " of the scenario")
    return {
        "score": round(score, 3),
        "components": {k: round(v, 3) for k, v in components.items()},
        "weights": WEIGHTS,
        "neighbourhood_tests": len(near),
        "not_recorded": not_recorded,
        "explanation": explanation,
    }


def rank(investigations: list[dict]) -> list[dict]:
    """Investigations with data, ordered by relevance (ties: more tests first). Others keep rank None."""
    scored = [i for i in investigations if i.get("relevance")]
    scored.sort(key=lambda i: (-i["relevance"]["score"], -i["data"]["tests"], i["investigation_id"]))
    for n, item in enumerate(scored, start=1):
        item["rank"] = n
    for item in investigations:
        item.setdefault("rank", None)
    return scored + [i for i in investigations if not i.get("relevance")]


# ---------------------------------------------------------------------------------------------- insights

def _evidence(tests: list[Canonical], variable: str, limit: int = 8) -> list[dict]:
    out = []
    for t in tests[:limit]:
        evidence_id = t.evidence(variable)
        if evidence_id:
            out.append({"evidence_id": evidence_id, "experiment_id": t.row.experiment_id, "test_id": t.row.test_id})
    return out


def _share(tests: list[Canonical], state: str) -> float | None:
    labelled = [t for t in tests if t.end_state]
    return None if not labelled else sum(t.end_state == state for t in labelled) / len(labelled)


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{round(100 * x)}%"


def insights(by_source: dict[str, list[Canonical]], scenario: Scenario, names: dict[str, str],
             model_estimate: dict | None = None, gravity_regimes: Iterable[str] = ()) -> list[dict]:
    out: list[dict] = []
    flexs = [t for t in by_source.get("FF-PSI-69", []) if t.end_state and t.o2 is not None]
    if flexs:
        low = [t for t in flexs if t.o2 < 0.16]
        high = [t for t in flexs if t.o2 >= 0.30]
        out.append({
            "insight_id": "flex_oxygen_vs_extinction",
            "title": "Lower oxygen, more self-extinguishing droplet flames",
            "kind": "measured_statistic",
            "investigations": ["FF-PSI-69"],
            "statement": (f"In FLEX, {_pct(_share(low, 'Extinction'))} of {len(low)} droplet flames at O₂ below 0.16 ended in "
                          f"extinction, versus {_pct(_share(high, 'Extinction'))} of {len(high)} at O₂ of 0.30 or more."),
            "numbers": {"low_o2": {"n": len(low), "extinction_share": _share(low, "Extinction")},
                        "high_o2": {"n": len(high), "extinction_share": _share(high, "Extinction")}},
            "evidence": _evidence(low, "test_end", 4) + _evidence(high, "test_end", 4),
            "caveats": ["Raw shares: pressure, diluent and droplet size also differ between these groups; the outcome "
                        "model separates their effects.",
                        "Evidence lists a sample of the tests' recorded end states (4 per group)."],
        })
        reduced = [t for t in flexs if t.pressure_kpa is not None and t.pressure_kpa <= 76]
        ambient = [t for t in flexs if t.pressure_kpa is not None and 95 <= t.pressure_kpa <= 106]
        if reduced and ambient:
            out.append({
                "insight_id": "flex_reduced_pressure",
                "title": "Reduced-pressure droplet tests",
                "kind": "measured_statistic",
                "investigations": ["FF-PSI-69"],
                "statement": (f"{len(reduced)} FLEX tests ran at or below 76 kPa (exploration-like pressure); "
                              f"{_pct(_share(reduced, 'Extinction'))} ended in extinction, versus "
                              f"{_pct(_share(ambient, 'Extinction'))} of {len(ambient)} tests near 1 atm."),
                "numbers": {"reduced": {"n": len(reduced), "extinction_share": _share(reduced, "Extinction")},
                            "ambient": {"n": len(ambient), "extinction_share": _share(ambient, "Extinction")}},
                "evidence": _evidence(reduced, "test_end", 4) + _evidence(ambient, "test_end", 4),
                "caveats": ["Oxygen fraction was not held constant between these groups.",
                            "Evidence lists a sample of the tests' recorded end states (4 per group)."],
            })
        near = neighbours(flexs, scenario)
        ends = Counter(t.end_state for t in near)
        out.append({
            "insight_id": "scenario_flex_neighbours",
            "title": f"Flight tests closest to: {scenario.name}",
            "kind": "measured_statistic" if near else "coverage_gap",
            "investigations": ["FF-PSI-69"],
            "statement": (
                f"{len(near)} FLEX droplet tests were flown within ±0.03 O₂ and ±25% pressure of this atmosphere "
                f"({scenario.o2_fraction:.2f} O₂, {scenario.pressure_kpa:.1f} kPa): "
                + ", ".join(f"{n} {state.lower()}" for state, n in sorted(ends.items())) + "."
                if near else
                f"No FLEX droplet test was flown within ±0.03 O₂ and ±25% pressure of this atmosphere "
                f"({scenario.o2_fraction:.2f} O₂, {scenario.pressure_kpa:.1f} kPa)."),
            "numbers": {"n": len(near), "end_states": dict(ends)},
            "evidence": _evidence(near, "test_end", 8),
            "caveats": ["Droplet combustion only; spacecraft materials are mostly solids."],
        })
    bass = [t for t in by_source.get("FF-PSI-25", []) if t.o2 is not None]
    if bass:
        top = max(t.o2 for t in bass)
        bottom = min(t.o2 for t in bass)
        covered = bottom - 1e-9 <= scenario.o2_fraction <= top + 1e-9
        out.append({
            "insight_id": "bass_solid_oxygen_coverage",
            "title": "Solid-material burns and enriched oxygen",
            "kind": "measured_statistic" if covered else "coverage_gap",
            "investigations": ["FF-PSI-25"],
            "statement": (f"BASS-II burned {len(bass)} solid samples ({len({t.material for t in bass if t.material})} distinct "
                          f"material descriptions in the table) at initial O₂ "
                          f"{min(t.o2 for t in bass):.3f}–{top:.3f}. "
                          + ("The scenario's O₂ lies inside that range." if covered else
                             f"No solid-material test in this table is at the scenario's {scenario.o2_fraction:.2f} O₂, so "
                             "solid-fuel behaviour there is not covered by BASS-II flight data.")),
            "numbers": {"n": len(bass), "o2_max": top},
            "evidence": _evidence(sorted(bass, key=lambda t: -t.o2), "calibrated_initial_o2_by_vol", 4),
            "caveats": ["The BASS-II table records conditions but no spread rate or extinction outcome; outcomes are in its "
                        "videos and summary report."],
        })
    if model_estimate:
        out.append(model_estimate)
    regimes = sorted(set(gravity_regimes))
    only_micro = regimes == ["microgravity"]
    without_outcomes = [names.get(s, s) for s, ts in by_source.items() if ts and not any(t.end_state or t.duration_s for t in ts)]
    out.append({
        "insight_id": "coverage_gaps",
        "title": "What this flight data cannot tell you",
        "kind": "coverage_gap",
        "investigations": sorted(by_source),
        "statement": (("Every flight test here ran in microgravity; none ran at lunar (1/6 g) or Martian (3/8 g) gravity, so "
                       "partial-gravity flame behaviour is not covered. " if only_micro else
                       f"Gravity regimes in this data: {', '.join(regimes) or 'none recorded'}. ")
                      + (f"{', '.join(without_outcomes)} record test conditions but no outcome in their tables."
                         if without_outcomes else "")).strip(),
        "numbers": {"gravity_regimes": regimes, "tables_without_outcomes": without_outcomes},
        "evidence": [],
        "caveats": [],
    })
    return out
