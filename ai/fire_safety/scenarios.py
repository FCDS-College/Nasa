"""Mission cabin atmospheres used to rank investigations by relevance.

Every value is quoted from, or derived arithmetically from, NASA/TM-2008-215260 p. 5
("Microgravity Flame Spread in Exploration Atmospheres", corpus source FF-NTRS-20080034883):

  "ISS ... have operated at normal sea-level conditions (air, 21% oxygen/79% nitrogen by volume at
  14.7 psia total pressure) except for brief pre-EVA activities when oxygen levels are increased
  for a short period of time to 30% oxygen while the total pressure is lowered to 10.2 psia."
  "The Crew Exploration Vehicle (CEV), Orion, and the lunar lander, Altair, are designed to operate
  from 8.0 to 14.9 psia and at a maximum of 30 and 34% oxygen concentration respectively ...
  the cabin pressure decreases to follow the normoxic curve which keeps the partial pressure of
  oxygen constant at the normal atmospheric air equivalent of 0.21 atm, or 3.09 psia."

Orion and Altair totals are therefore *derived*: total = 3.09 psia / O2 fraction on that curve.
No source in the corpus gives a Mars habitat atmosphere, and every flight test here is in
microgravity, so no scenario claims lunar or Martian partial-gravity behaviour.

Historical scenarios (ADR-013) are data, not code: one JSON file per scenario in ``historical/``,
validated against ``historical/historical_scenario.schema.json``. Each carries its own atmosphere,
gravity, a page-cited story and timeline, and the in-envelope alternative to show after the refusal.
Adding a future incident (Apollo 13, Mir 1997, ...) means adding a file, not changing this module.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

KPA_PER_PSIA = 6.894757
NORMOXIC_PPO2_PSIA = 3.09
CITATION = "NASA/TM-2008-215260 (FF-NTRS-20080034883), p. 5"
GRAVITY = ("microgravity", "lunar", "martian", "earth")
FLIGHT_GRAVITY = "microgravity"   # every flight test in the corpus (ISS and free-flyer experiments)
HISTORICAL_DIR = Path(__file__).resolve().parent / "historical"


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    name: str
    o2_fraction: float
    pressure_kpa: float
    basis: str            # quoted | derived | user | historical
    note: str
    citation: str | None = CITATION
    gravity: str = FLIGHT_GRAVITY       # microgravity | lunar | martian | earth
    kind: str = "mission"               # mission | historical | custom

    @property
    def ppo2_kpa(self) -> float:
        return self.o2_fraction * self.pressure_kpa

    def as_dict(self) -> dict:
        data = asdict(self)
        data["ppo2_kpa"] = round(self.ppo2_kpa, 2)
        data["pressure_kpa"] = round(self.pressure_kpa, 2)
        return data


def _normoxic_kpa(o2: float) -> float:
    return NORMOXIC_PPO2_PSIA / o2 * KPA_PER_PSIA


MISSION_SCENARIOS: tuple[Scenario, ...] = (
    Scenario("iss_nominal", "ISS cabin (nominal)", 0.21, 14.7 * KPA_PER_PSIA, "quoted",
             "Sea-level air at 14.7 psia, as flown on Skylab, Shuttle and ISS."),
    Scenario("pre_eva", "Pre-EVA campout", 0.30, 10.2 * KPA_PER_PSIA, "quoted",
             "Brief pre-EVA atmosphere; many ISS materials are only rated to it."),
    Scenario("orion_max_o2", "Orion crew vehicle (max O₂)", 0.30, _normoxic_kpa(0.30), "derived",
             "Orion maximum 30% O₂; total pressure from the normoxic curve (ppO₂ 3.09 psia)."),
    Scenario("lunar_lander_max_o2", "Lunar lander, Altair class (max O₂)", 0.34, _normoxic_kpa(0.34), "derived",
             "Altair maximum 34% O₂; total pressure from the normoxic curve. Gravity in the cabin on the "
             "lunar surface is 1/6 g, which no flight test here covers."),
)


@dataclass(frozen=True)
class History:
    """The cited story behind a historical scenario (served by GET /api/scenarios/{id}/history)."""
    scenario_id: str
    year: int
    story: str
    lesson: str
    lesson_sources: tuple[dict, ...]
    timeline: tuple[dict, ...]
    alternative: dict
    raw: dict = field(repr=False, compare=False, default_factory=dict)


_REQUIRED = ("scenario_id", "name", "year", "o2_fraction", "pressure_kpa", "gravity", "note", "citation",
             "story", "lesson", "lesson_sources", "timeline", "alternative")


def _sources_ok(items: object) -> bool:
    return (isinstance(items, list) and bool(items)
            and all(isinstance(i, dict) and str(i.get("source_id", "")).startswith("FF-NTRS-")
                    and isinstance(i.get("page"), int) and i["page"] >= 1 for i in items))


def _check(data: dict, path: Path) -> None:
    """Runtime structural check (the full JSON Schema is enforced in CI by tests/unit, with jsonschema)."""
    missing = [k for k in _REQUIRED if k not in data]
    problems = [f"missing {', '.join(missing)}"] if missing else []
    if not missing:
        if data["gravity"] not in GRAVITY:
            problems.append(f"gravity must be one of {GRAVITY}")
        if not 0.05 <= float(data["o2_fraction"]) <= 1.0:
            problems.append("o2_fraction must be between 0.05 and 1.0")
        if not 5.0 <= float(data["pressure_kpa"]) <= 400.0:
            problems.append("pressure_kpa must be between 5 and 400")
        if not _sources_ok(data["lesson_sources"]):
            problems.append("lesson_sources need an FF-NTRS source_id and a page")
        if not data["timeline"] or not all(_sources_ok(e.get("sources")) for e in data["timeline"]):
            problems.append("every timeline event needs at least one FF-NTRS source with a page")
        if not _sources_ok(data["alternative"].get("sources")):
            problems.append("the alternative needs an FF-NTRS source with a page")
    if problems:
        raise ValueError(f"{path.name}: " + "; ".join(problems))


def load_historical(directory: Path = HISTORICAL_DIR) -> tuple[tuple[Scenario, ...], dict[str, History]]:
    scenarios: list[Scenario] = []
    histories: dict[str, History] = {}
    for path in sorted(directory.glob("*.json")):
        if path.name.endswith(".schema.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        _check(data, path)
        sid = data["scenario_id"]
        scenarios.append(Scenario(sid, data["name"], float(data["o2_fraction"]), float(data["pressure_kpa"]),
                                  "historical", data["note"], data["citation"], data["gravity"], "historical"))
        histories[sid] = History(sid, int(data["year"]), data["story"], data["lesson"], tuple(data["lesson_sources"]),
                                 tuple(data["timeline"]), dict(data["alternative"]), data)
    return tuple(scenarios), histories


HISTORICAL_SCENARIOS, HISTORIES = load_historical()
SCENARIOS: tuple[Scenario, ...] = MISSION_SCENARIOS + HISTORICAL_SCENARIOS
BY_ID = {s.scenario_id: s for s in SCENARIOS}
for _h in HISTORIES.values():   # an alternative must be a scenario the dashboard can load
    if _h.alternative["scenario_id"] not in BY_ID:
        raise ValueError(f"{_h.scenario_id}: alternative {_h.alternative['scenario_id']!r} is not a known scenario")


def custom(o2_fraction: float, pressure_kpa: float, gravity: str = FLIGHT_GRAVITY) -> Scenario:
    if not 0.05 <= o2_fraction <= 1.0:
        raise ValueError("o2_fraction must be between 0.05 and 1.0")
    if not 5.0 <= pressure_kpa <= 400.0:
        raise ValueError("pressure_kpa must be between 5 and 400")
    if gravity not in GRAVITY:
        raise ValueError(f"gravity must be one of {', '.join(GRAVITY)}")
    return Scenario("custom", "Custom atmosphere", o2_fraction, pressure_kpa, "user",
                    "User-supplied atmosphere.", None, gravity, "custom")
