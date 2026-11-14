"""Turn an extinguisher discharge into an atmosphere, and score an atmosphere's heat-sink capacity.

Model (plan §3.1): ideal gas, ventilation off (the ISS fire response stops ventilation first),
instant mixing within the volume the discharge fills.

* **well-mixed**: the whole cabin; the conservative floor for suppression and the basis for crew hazards;
* **local**: a fire zone that is ``zone_fraction`` of the cabin, for an aimed discharge.
  The zone is open to the cabin, so its pressure is the cabin's post-discharge pressure.

Water mist: the nitrogen propellant is added as gas; only ``delivery_fraction`` (η) of the water
reaches the fire zone, as liquid. Undelivered water never enters the fire-zone balance.

Effective enthalpy per mole of O₂ (Sheinson et al. 1989; used for CO₂/N₂/He in microgravity by
Ruff et al., NTRS 20040161262): the energy to heat everything that accompanies one mole of O₂ from
298 K to 1600 K. For delivered liquid water this includes vaporisation. Fuel is excluded.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ai.fire_safety.suppression import constants as C

GASES = ("O2", "N2", "CO2", "He")
AGENTS = ("co2", "water_mist")


@dataclass(frozen=True)
class Atmosphere:
    pressure_kpa: float
    x: dict[str, float]                       # gas mole fractions, sum to 1
    liquid_water_per_mol_gas: float = 0.0     # mol of delivered liquid water per mol of gas

    @property
    def pressure_atm(self) -> float:
        return self.pressure_kpa / 101.325

    def partial_pressure_mmhg(self, gas: str) -> float:
        return self.x.get(gas, 0.0) * self.pressure_kpa * C.MMHG_PER_KPA

    def as_dict(self) -> dict:
        return {"pressure_kpa": round(self.pressure_kpa, 3),
                "mole_fractions": {g: round(v, 6) for g, v in self.x.items()},
                "liquid_water_mol_per_mol_gas": round(self.liquid_water_per_mol_gas, 6),
                "ppo2_kpa": round(self.x["O2"] * self.pressure_kpa, 3),
                "ppco2_mmhg": round(self.partial_pressure_mmhg("CO2"), 3)}


def cabin(pressure_kpa: float, o2: float, co2: float = 0.0, he: float = 0.0) -> Atmosphere:
    if not 0 < o2 < 1 or co2 < 0 or he < 0 or o2 + co2 + he > 1 + 1e-9:
        raise ValueError("mole fractions must be non-negative with O2 + CO2 + He <= 1")
    if pressure_kpa <= 0:
        raise ValueError("pressure must be positive")
    return Atmosphere(pressure_kpa, {"O2": o2, "N2": max(0.0, 1.0 - o2 - co2 - he), "CO2": co2, "He": he})


@dataclass(frozen=True)
class Discharge:
    agent: str
    zone: Atmosphere            # what the fire sees
    cabin_after: Atmosphere     # whole cabin, well mixed: crew hazards
    moles: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"agent": self.agent, "fire_zone": self.zone.as_dict(), "cabin_after": self.cabin_after.as_dict(),
                "moles": {k: round(v, 4) for k, v in self.moles.items()}}


def _mix(base: Atmosphere, n_base: float, add: dict[str, float]) -> tuple[dict[str, float], float]:
    moles = {g: base.x.get(g, 0.0) * n_base + add.get(g, 0.0) for g in GASES}
    total = sum(moles.values())
    return {g: moles[g] / total for g in GASES}, total


def discharge(before: Atmosphere, agent: str, volume_m3: float, temperature_k: float = C.DEFAULT_CABIN_TEMPERATURE_K,
              zone_fraction: float = 1.0, delivery_fraction: float = 1.0,
              co2_kg: float | None = None, water_kg: float | None = None, nitrogen_kg: float | None = None) -> Discharge:
    """Post-discharge fire-zone and whole-cabin atmospheres for one PFE."""
    if agent not in AGENTS:
        raise ValueError(f"agent must be one of {AGENTS}")
    if volume_m3 <= 0 or temperature_k <= 0:
        raise ValueError("volume and temperature must be positive")
    if not 0 < zone_fraction <= 1:
        raise ValueError("zone_fraction must be in (0, 1]")
    if not 0 <= delivery_fraction <= 1:
        raise ValueError("delivery_fraction must be in [0, 1]")

    n_cabin = before.pressure_kpa * 1e3 * volume_m3 / (C.R * temperature_k)
    n_zone = n_cabin * zone_fraction
    if agent == "co2":
        n_co2 = (C.CO2_PFE["agent_kg"] if co2_kg is None else co2_kg) / C.M_CO2
        gas_added, liquid = {"CO2": n_co2}, 0.0
        moles = {"cabin_gas": n_cabin, "fire_zone_gas": n_zone, "co2_added": n_co2}
    else:
        n_n2 = (C.FWM_PFE["nitrogen_kg"] if nitrogen_kg is None else nitrogen_kg) / C.M_N2
        n_water = (C.FWM_PFE["water_kg"] if water_kg is None else water_kg) / C.M_H2O
        gas_added, liquid = {"N2": n_n2}, n_water * delivery_fraction
        moles = {"cabin_gas": n_cabin, "fire_zone_gas": n_zone, "n2_added": n_n2, "water_discharged": n_water,
                 "water_delivered": liquid}

    x_cabin, n_cabin_after = _mix(before, n_cabin, gas_added)
    p_after = before.pressure_kpa * n_cabin_after / n_cabin
    x_zone, n_zone_after = _mix(before, n_zone, gas_added)
    zone = Atmosphere(p_after, x_zone, liquid / n_zone_after)
    return Discharge(agent, zone, Atmosphere(p_after, x_cabin), moles)


def effective_enthalpy(atm: Atmosphere) -> float:
    """kJ to heat the gas and delivered water accompanying one mol of O₂ from 298 K to 1600 K."""
    o2 = atm.x["O2"]
    if o2 <= 0:
        raise ValueError("no oxygen: the criterion is undefined")
    gas = sum(atm.x.get(g, 0.0) * C.DH_GAS_KJ[g] for g in GASES)
    return (gas + atm.liquid_water_per_mol_gas * C.DH_WATER_LIQUID_TO_1600_KJ) / o2


def flex_features(atm: Atmosphere, fuel: str, d0_mm: float) -> dict[str, float]:
    """The FLEX outcome model's inputs for an atmosphere (water is not a FLEX input and is ignored)."""
    p_atm = atm.pressure_atm
    return {"o2": atm.x["O2"], "pressure_atm": p_atm, "ppo2_atm": atm.x["O2"] * p_atm, "co2": atm.x["CO2"],
            "he": atm.x["He"], "d0_mm": d0_mm, "heptane": 1.0 if fuel == "Heptane" else 0.0}


def mist_atmosphere(omega_w: float, phi: float = C.MIST_PHI) -> Atmosphere:
    """A MIST test (premixed propane–air, 1 atm) as an atmosphere: air plus ω_w kg water per kg gas.

    Fuel is excluded from the criterion, as for every other atmosphere; it enters only the gas mass.
    """
    air_o2 = 0.21
    fuel_per_mol_air = phi * air_o2 / 5.0                # C3H8 + 5 O2: stoichiometric fuel/air = 0.21/5
    gas_g_per_mol_air = 28.96 + fuel_per_mol_air * 44.097
    mol_air_per_kg_gas = 1000.0 / gas_g_per_mol_air
    water_mol_per_kg_gas = omega_w / C.M_H2O
    return Atmosphere(101.325, {"O2": air_o2, "N2": 1 - air_o2, "CO2": 0.0, "He": 0.0},
                      water_mol_per_kg_gas / mol_air_per_kg_gas)
