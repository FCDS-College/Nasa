"""Crew-hazard checks after a discharge (plan §3.4). Rules and sourced limits only, never a model.

Levels: ``red`` (the agent is vetoed), ``amber`` (caution), ``green`` (within the limit), ``info``
(reported without a verdict because no sourced limit is held for it).
Every check is on the **whole cabin, well mixed**: that is what the crew breathes.
"""
from __future__ import annotations

from ai.fire_safety.suppression import constants as C
from ai.fire_safety.suppression.discharge import Atmosphere, Discharge


def ppco2_check(atm: Atmosphere) -> dict:
    value = atm.partial_pressure_mmhg("CO2")
    if value >= C.PPCO2_IDLH_MMHG:
        level, text = "red", (f"Cabin ppCO₂ {value:.1f} mmHg reaches the CO₂ IDLH ({C.PPCO2_IDLH_MMHG:.1f} mmHg, "
                              f"40,000 ppm at 1 atm): immediately dangerous to life without a breathing apparatus.")
    elif value >= C.PPCO2_1H_LIMIT_MMHG:
        level, text = "amber", (f"Cabin ppCO₂ {value:.1f} mmHg is above the NASA-STD-3001 one-hour average limit "
                                f"({C.PPCO2_1H_LIMIT_MMHG:.0f} mmHg) but below the IDLH.")
    else:
        level, text = "green", f"Cabin ppCO₂ {value:.1f} mmHg is within the NASA-STD-3001 one-hour average limit."
    return {"hazard": "cabin_ppco2", "level": level, "value": round(value, 2), "unit": "mmHg",
            "limits": {"one_hour_average": C.PPCO2_1H_LIMIT_MMHG, "idlh": round(C.PPCO2_IDLH_MMHG, 1)},
            "statement": text, "claim_class": "reference",
            "sources": ["NASA-STD-3001 Vol. 2 [V2 6004]", "NIOSH IDLH, carbon dioxide (cdc.gov/niosh/idlh/124389.html)"],
            "assumption": "IDLH applied as a partial pressure (0.04 × 760 mmHg)"}


def min_volume_for_co2(before: Atmosphere, temperature_k: float = C.DEFAULT_CABIN_TEMPERATURE_K) -> float:
    """Cabin volume below which one CO₂ PFE, well mixed, reaches the IDLH.

    Well mixed, ppCO₂ after = ppCO₂ before + n_CO₂·R·T/V, so V = n_CO₂·R·T / (IDLH − ppCO₂ before).
    """
    n_co2 = C.CO2_PFE["agent_kg"] / C.M_CO2
    headroom_pa = (C.PPCO2_IDLH_MMHG - before.partial_pressure_mmhg("CO2")) / C.MMHG_PER_KPA * 1e3
    return float("inf") if headroom_pa <= 0 else n_co2 * C.R * temperature_k / headroom_pa


def assess(before: Atmosphere, d: Discharge) -> list[dict]:
    after = d.cabin_after
    checks = [ppco2_check(after)]
    checks.append({"hazard": "cabin_ppo2", "level": "info", "value": round(after.x["O2"] * after.pressure_kpa, 2),
                   "before": round(before.x["O2"] * before.pressure_kpa, 2), "unit": "kPa",
                   "statement": "O₂ partial pressure after the discharge (dilution only; no sourced limit held).",
                   "claim_class": "computed"})
    checks.append({"hazard": "cabin_pressure", "level": "info", "value": round(after.pressure_kpa, 2),
                   "before": round(before.pressure_kpa, 2), "unit": "kPa",
                   "statement": "Cabin pressure after the discharge, ventilation off.", "claim_class": "computed"})
    if d.agent == "co2":
        checks.append({"hazard": "breathing_apparatus", "level": "amber", "statement": C.CO2_BREATHING_RULE["statement"],
                       "claim_class": "reference", "sources": [C.CO2_BREATHING_RULE["source"]]})
    else:
        for flag in C.WATER_MIST_FLAGS:
            checks.append({"hazard": flag["flag"], "level": "amber", "statement": flag["statement"],
                           "claim_class": "reference", "sources": [flag["source"]]})
    return checks


def worst(checks: list[dict]) -> str:
    order = {"red": 3, "amber": 2, "green": 1, "info": 0}
    return max((c["level"] for c in checks), key=order.get, default="info")
