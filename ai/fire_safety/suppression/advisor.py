"""Suppression Advisor: deterministic recommendation between the ISS CO₂ and Fine Water Mist PFEs.

No language model is involved; the same inputs always give the same answer (plan §3.5).

What each fire type may show (D4):
* heptane / methanol: FLEX estimate for CO₂ (``estimated``), thermal-model estimates (``computed``),
  the crossover delivery fraction η*, hazards;
* other liquid / unknown fuel: η* and hazards only (fuel-independent approximation);
* electrical / battery: a sourced rule and hazards only;
* solid: hazards and evidence links only.

The absolute water-mist probability appears only when both D2 gates in the thermal model's
evaluation file passed.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass

from ai.fire_safety.suppression import constants as C
from ai.fire_safety.suppression import discharge as D
from ai.fire_safety.suppression import hazards as H
from ai.fire_safety.suppression import thermal as T

FIRE_TYPES = ("heptane", "methanol", "other_liquid", "electrical_battery", "solid")
FLEX_FUEL = {"heptane": "Heptane", "methanol": "Methanol"}
ZONES = ("well_mixed", "local")

DISCLAIMER = ("Decision support only. It does not replace flight rules or the emergency procedure: when in doubt, "
              "follow the flight rule.")
SCOPE = ("Built from FLEX droplet-flame flight tests (heptane, methanol), the MIST water-mist flight experiment, ISS "
         "extinguisher test papers and published exposure limits. Water-mist suppression is computed, not "
         "flight-validated at cabin scale.")
EVIDENCE = [
    {"id": "FF-PSI-69", "title": "FLEX droplet extinction flight tests (CO₂ and He diluent)", "kind": "flight_data"},
    {"id": "NIST R0401173", "title": "MIST water-mist suppression, STS-107 (microgravity)", "kind": "literature"},
    {"id": "NTRS 20130011664", "title": "ISS Fine Water Mist PFE development and fire tests", "kind": "literature"},
    {"id": "NTRS 20040161262", "title": "CO₂, N₂ and He as suppressants in microgravity; ISS CO₂ PFE", "kind": "literature"},
]
SOLID_EVIDENCE = [
    {"id": "FF-PSI-25", "title": "BASS-II: burning and suppression of solids", "kind": "flight_data"},
    {"id": "FF-PSI-26", "title": "BASS: burning and suppression of solids", "kind": "flight_data"},
]


@dataclass(frozen=True)
class AdviceInput:
    fire_type: str = "heptane"
    cabin_volume_m3: float = C.DEFAULT_CABIN_VOLUME_M3
    pressure_kpa: float = 101.3
    o2_fraction: float = 0.21
    co2_fraction: float = 0.0
    temperature_k: float = C.DEFAULT_CABIN_TEMPERATURE_K
    zone: str = "well_mixed"
    local_zone_fraction: float = C.DEFAULT_LOCAL_ZONE_FRACTION
    delivery_fraction: float = C.DEFAULT_DELIVERY_FRACTION
    droplet_diameter_mm: float = 3.0

    def validate(self) -> None:
        if self.fire_type not in FIRE_TYPES:
            raise ValueError(f"fire_type must be one of {FIRE_TYPES}")
        if self.zone not in ZONES:
            raise ValueError(f"zone must be one of {ZONES}")


def _kcal(kj: float) -> float:
    return round(kj / C.KJ_PER_KCAL, 2)


def crossover_delivery_fraction(before: D.Atmosphere, inp: AdviceInput, zone_fraction: float) -> float | None:
    """η* at which the water-mist fire zone's effective enthalpy equals the CO₂ fire zone's.

    None when even full delivery of the water removes less heat than the CO₂ discharge.
    """
    target = D.effective_enthalpy(D.discharge(before, "co2", inp.cabin_volume_m3, inp.temperature_k, zone_fraction).zone)

    def h_water(eta):
        return D.effective_enthalpy(D.discharge(before, "water_mist", inp.cabin_volume_m3, inp.temperature_k,
                                                zone_fraction, eta).zone)
    if h_water(1.0) < target:
        return None
    if h_water(0.0) >= target:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if h_water(mid) < target else (lo, mid)
    return round(hi, 4)


def advise(inp: AdviceInput, flex_predict: Callable[[dict], dict] | None = None) -> dict:
    """``flex_predict(features) -> {"probabilities", "applicability", "similar_tests", ...}`` is the FLEX
    outcome model with its nearest flight tests (the API passes ``investigations.predict``)."""
    inp.validate()
    before = D.cabin(inp.pressure_kpa, inp.o2_fraction, inp.co2_fraction)
    zone_fraction = 1.0 if inp.zone == "well_mixed" else inp.local_zone_fraction
    model = T.load()
    gates = model.gates()
    fuel = FLEX_FUEL.get(inp.fire_type)
    liquid = inp.fire_type in ("heptane", "methanol", "other_liquid")

    discharges = {
        "co2": D.discharge(before, "co2", inp.cabin_volume_m3, inp.temperature_k, zone_fraction),
        "water_mist": D.discharge(before, "water_mist", inp.cabin_volume_m3, inp.temperature_k, zone_fraction,
                                  inp.delivery_fraction),
    }
    agents = {}
    for name, d in discharges.items():
        h = D.effective_enthalpy(d.zone)
        checks = H.assess(before, d)
        entry = {"agent": name, "extinguisher": "ISS CO₂ PFE" if name == "co2" else "ISS Fine Water Mist PFE",
                 "charge": C.CO2_PFE if name == "co2" else C.FWM_PFE, "post_discharge": d.as_dict(),
                 "effective_enthalpy_kcal_per_mol_o2": _kcal(h) if liquid else None,
                 "hazards": checks, "hazard_level": H.worst(checks),
                 "flex_estimate": None, "thermal_estimate": None, "withheld": []}
        if fuel:
            app = model.applicability(h, d.zone.pressure_atm, fuel)
            allowed = gates["model_signal_ok"] and (name == "co2" or gates["water_probability_allowed"])
            if allowed and app["in_domain"]:
                entry["thermal_estimate"] = {"p_extinction": round(model.p_extinction(h, d.zone.pressure_atm, fuel), 4),
                                             "claim_class": "computed", "model_version": model.version}
            elif not allowed:
                entry["withheld"].append("Absolute water-mist probability withheld: the thermal model failed the MIST "
                                         "check (it over-predicts water-mist suppression of the MIST flames)."
                                         if gates["model_signal_ok"] else
                                         "Thermal-model probabilities withheld: the model failed the FLEX signal check.")
            else:
                entry["withheld"].append("Thermal-model probability withheld: " + "; ".join(app["reasons"]))
            if name == "co2" and flex_predict is not None:
                result = flex_predict(D.flex_features(d.zone, fuel, inp.droplet_diameter_mm))
                p = result.get("probabilities")
                entry["flex_estimate"] = {"p_extinction": None if p is None else p["Extinction"],
                                          "probabilities": p, "applicability": result.get("applicability"),
                                          "similar_tests": result.get("similar_tests", []), "claim_class": "estimated"}
        agents[name] = entry

    eta_star = crossover_delivery_fraction(before, inp, zone_fraction) if liquid else None
    decision = _decide(inp, agents, eta_star)
    v_red = H.min_volume_for_co2(before, inp.temperature_k)
    return {
        "input": asdict(inp),
        "assumptions": {"cabin_volume_m3": "example value unless you enter your module's free volume "
                                           f"(sourced preset: ISS airlock {C.AIRLOCK_VOLUME_M3:.0f} m³)",
                        "zone": "well-mixed is the conservative floor; local assumes the discharge fills "
                                f"{inp.local_zone_fraction:.0%} of the cabin",
                        "delivery_fraction": "η, the share of the water reaching the fire as fine mist: an assumption",
                        "ventilation": "off, per the ISS fire response"},
        **decision,
        "crossover_delivery_fraction": None if not liquid else {
            "value": eta_star, "claim_class": "computed",
            "statement": (f"Water mist removes more heat than CO₂ here if at least {eta_star:.0%} of it reaches the fire."
                          if eta_star is not None else
                          "Even if all the water reaches the fire, it removes less heat than the CO₂ discharge here."),
            "basis": "effective enthalpy per mol O₂ (298→1600 K), fuel-independent approximation"},
        "co2_idlh_volume_m3": round(v_red, 1),
        "agents": agents,
        "gates": gates,
        "evidence": EVIDENCE + (SOLID_EVIDENCE if inp.fire_type == "solid" else []),
        "scope": SCOPE,
        "disclaimer": DISCLAIMER,
    }


def _decide(inp: AdviceInput, agents: dict, eta_star: float | None) -> dict:
    co2, water = agents["co2"], agents["water_mist"]
    change = []
    if eta_star is not None:
        change.append(f"How much of the mist reaches the fire: above {eta_star:.0%} water mist removes more heat than CO₂.")
    change.append("A smaller cabin raises the CO₂ concentration the crew breathes after a CO₂ discharge.")

    if inp.fire_type == "solid":
        return _out("no_recommendation", None, "none", "out_of_scope",
                    ["No flight-validated suppression model for solid materials yet (model support planned).",
                     "Use the crew-hazard checks below and the BASS evidence; follow the flight rule."], change)
    if inp.fire_type == "electrical_battery":
        why = [C.BATTERY_RULE["statement"], "Remove power first, per the fire response procedure."]
        if co2["hazard_level"] == "red":
            why.append("A CO₂ discharge would also reach the CO₂ IDLH in this cabin.")
        return _out("recommend", "water_mist", "low", "sourced_rule", why, change, sources=[C.BATTERY_RULE["source"]])
    if co2["hazard_level"] == "red":
        return _out("recommend", "water_mist", "moderate", "hazard_veto",
                    [next(c["statement"] for c in co2["hazards"] if c["hazard"] == "cabin_ppco2"),
                     "CO₂ is ruled out on crew safety, so the water-mist extinguisher is recommended."], change)

    p_co2 = (co2["thermal_estimate"] or {}).get("p_extinction")
    p_water = (water["thermal_estimate"] or {}).get("p_extinction")
    if p_co2 is not None and p_water is not None:
        margin = abs(p_co2 - p_water)
        if margin >= C.CLEAR_WINNER_MARGIN:
            winner = "co2" if p_co2 > p_water else "water_mist"
            confidence = "high" if margin >= C.HIGH_CONFIDENCE_MARGIN else "moderate"
            return _out("recommend", winner, confidence, "thermal_model_comparison",
                        [f"On one model, P(extinction) is {p_co2:.0%} for CO₂ and {p_water:.0%} for water mist at "
                         f"{inp.delivery_fraction:.0%} delivery."], change)
        return _out("no_clear_winner", None, "low", "thermal_model_comparison",
                    [f"P(extinction) is {p_co2:.0%} for CO₂ and {p_water:.0%} for water mist: too close to call."], change)
    why = ["Neither extinguisher is ruled out on crew safety, and an absolute comparison is not supported here."]
    if eta_star is not None:
        why.append(f"Water mist removes more heat if at least {eta_star:.0%} of it reaches the fire; "
                   f"your assumed delivery is {inp.delivery_fraction:.0%}.")
    return _out("no_clear_winner", None, "low", "relative_only", why, change)


def _out(outcome, agent, confidence, basis, why, change, sources=None) -> dict:
    return {"outcome": outcome, "recommended_agent": agent, "confidence": confidence, "basis": basis,
            "why": why, "what_would_change_it": change, "decision_sources": sources or []}
