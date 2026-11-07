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
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

KPA_PER_PSIA = 6.894757
NORMOXIC_PPO2_PSIA = 3.09
CITATION = "NASA/TM-2008-215260 (FF-NTRS-20080034883), p. 5"


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    name: str
    o2_fraction: float
    pressure_kpa: float
    basis: str            # quoted | derived | user
    note: str
    citation: str | None = CITATION

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


SCENARIOS: tuple[Scenario, ...] = (
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
BY_ID = {s.scenario_id: s for s in SCENARIOS}


def custom(o2_fraction: float, pressure_kpa: float) -> Scenario:
    if not 0.05 <= o2_fraction <= 1.0:
        raise ValueError("o2_fraction must be between 0.05 and 1.0")
    if not 5.0 <= pressure_kpa <= 400.0:
        raise ValueError("pressure_kpa must be between 5 and 400")
    return Scenario("custom", "Custom atmosphere", o2_fraction, pressure_kpa, "user",
                    "User-supplied atmosphere.", None)
