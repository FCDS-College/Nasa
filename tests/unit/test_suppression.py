"""Suppression Advisor: discharge physics, thermal model, D2 gates, D4 fire-type matrix, decisions."""
import json

import pytest

from ai.fire_safety.suppression import advisor as A
from ai.fire_safety.suppression import calibrate
from ai.fire_safety.suppression import constants as C
from ai.fire_safety.suppression import discharge as D
from ai.fire_safety.suppression import hazards as H
from ai.fire_safety.suppression import thermal as T

AIR = D.cabin(101.325, 0.21)


# ---------------------------------------------------------------- discharge physics

@pytest.mark.parametrize("agent", D.AGENTS)
@pytest.mark.parametrize("zone_fraction", [1.0, 0.1])
def test_mole_fractions_sum_to_one_and_agent_moles_are_conserved(agent, zone_fraction):
    d = D.discharge(AIR, agent, 50.0, zone_fraction=zone_fraction, delivery_fraction=0.7)
    for atm in (d.zone, d.cabin_after):
        assert sum(atm.x.values()) == pytest.approx(1.0)
    n_after = d.moles["cabin_gas"] * d.cabin_after.pressure_kpa / AIR.pressure_kpa
    gas = "CO2" if agent == "co2" else "N2"
    added = d.moles["co2_added"] if agent == "co2" else d.moles["n2_added"]
    assert d.cabin_after.x[gas] * n_after == pytest.approx(AIR.x[gas] * d.moles["cabin_gas"] + added)


def test_ppco2_rise_matches_closed_form():
    d = D.discharge(AIR, "co2", 100.0)
    n = C.CO2_PFE["agent_kg"] / C.M_CO2
    expected_mmhg = n * C.R * C.DEFAULT_CABIN_TEMPERATURE_K / 100.0 / 1e3 * C.MMHG_PER_KPA
    assert d.cabin_after.partial_pressure_mmhg("CO2") == pytest.approx(expected_mmhg)


def test_undelivered_water_never_enters_the_fire_zone():
    none = D.discharge(AIR, "water_mist", 100.0, delivery_fraction=0.0)
    assert none.zone.liquid_water_per_mol_gas == 0.0
    half = D.discharge(AIR, "water_mist", 100.0, delivery_fraction=0.5)
    full = D.discharge(AIR, "water_mist", 100.0, delivery_fraction=1.0)
    assert half.zone.liquid_water_per_mol_gas == pytest.approx(full.zone.liquid_water_per_mol_gas / 2)


def test_more_agent_never_lowers_effective_enthalpy():
    h = [D.effective_enthalpy(D.discharge(AIR, "co2", 100.0, co2_kg=m).zone) for m in (0.5, 1, 2, 4)]
    assert h == sorted(h)
    h = [D.effective_enthalpy(D.discharge(AIR, "water_mist", 100.0, delivery_fraction=e).zone) for e in (0, .25, .5, 1)]
    assert h == sorted(h)


def test_air_effective_enthalpy_and_water_heat_sink():
    assert D.effective_enthalpy(AIR) / C.KJ_PER_KCAL == pytest.approx(48.25, abs=0.05)
    assert C.DH_WATER_LIQUID_TO_1600_KJ == pytest.approx(96.91, abs=0.01)
    per_kg_water = C.DH_WATER_LIQUID_TO_1600_KJ / C.M_H2O
    per_kg_co2 = C.DH_GAS_KJ["CO2"] / C.M_CO2
    assert 3.0 < per_kg_water / per_kg_co2 < 4.0      # the ~3x heat-sink ratio behind η*


@pytest.mark.parametrize("bad", [dict(o2=0.0), dict(o2=0.6, co2=0.5), dict(o2=0.2, co2=-0.1)])
def test_invalid_atmospheres_are_rejected(bad):
    with pytest.raises(ValueError):
        D.cabin(101.3, **bad)


def test_invalid_discharge_arguments_are_rejected():
    with pytest.raises(ValueError):
        D.discharge(AIR, "halon", 10.0)
    with pytest.raises(ValueError):
        D.discharge(AIR, "co2", 10.0, zone_fraction=0.0)
    with pytest.raises(ValueError):
        D.discharge(AIR, "water_mist", 10.0, delivery_fraction=1.5)


# ---------------------------------------------------------------- thermal model and gates

def test_thermal_probability_increases_with_effective_enthalpy():
    m = T.load()
    p = [m.p_extinction(h, 1.0, "Heptane") for h in (150, 200, 250, 300)]
    assert p == sorted(p) and p[0] < p[-1]
    assert m.p_extinction(m.h50(1.0, "Heptane"), 1.0, "Heptane") == pytest.approx(0.5, abs=1e-9)


def test_gates_are_read_from_the_evaluation_file():
    evaluation = json.loads(T.EVALUATION.read_text(encoding="utf-8"))
    g = T.load().gates()
    assert g["model_signal_ok"] == evaluation["gates"]["flex_auc"]["passed"]
    assert g["water_probability_allowed"] == (evaluation["gates"]["flex_auc"]["passed"]
                                              and evaluation["gates"]["mist"]["passed"])
    lower = evaluation["repeated_grouped_cv"]["extinction_roc_auc"]
    assert evaluation["gates"]["flex_auc"]["lower_bound"] == pytest.approx(lower["mean"] - lower["sd"], abs=1e-4)


def test_artefacts_are_current():
    assert calibrate.is_current(), "rerun: python -m ai.fire_safety.suppression.calibrate"


# ---------------------------------------------------------------- advisor

def _with_gates(monkeypatch, water_allowed: bool):
    real = T.load()
    evaluation = json.loads(json.dumps(real.evaluation))
    evaluation["gates"]["flex_auc"]["passed"] = True
    evaluation["gates"]["mist"]["passed"] = water_allowed
    model = T.ThermalModel(real.artefact, evaluation)
    monkeypatch.setattr(T, "load", lambda: model)


def test_same_inputs_give_the_same_answer():
    assert A.advise(A.AdviceInput()) == A.advise(A.AdviceInput())


def test_co2_over_the_idlh_is_never_recommended():
    small = A.AdviceInput(cabin_volume_m3=C.AIRLOCK_VOLUME_M3)
    r = A.advise(small)
    assert r["agents"]["co2"]["hazard_level"] == "red"
    assert r["recommended_agent"] != "co2" and r["basis"] == "hazard_veto"
    assert H.min_volume_for_co2(D.cabin(101.3, 0.21)) == pytest.approx(r["co2_idlh_volume_m3"], abs=0.1)
    assert A.advise(A.AdviceInput(cabin_volume_m3=r["co2_idlh_volume_m3"] + 1))["agents"]["co2"]["hazard_level"] != "red"


def test_crossover_delivery_fraction_balances_the_two_heat_sinks():
    inp = A.AdviceInput()
    eta = A.advise(inp)["crossover_delivery_fraction"]["value"]
    assert 0 < eta < 1
    before = D.cabin(inp.pressure_kpa, inp.o2_fraction)
    co2 = D.effective_enthalpy(D.discharge(before, "co2", inp.cabin_volume_m3, inp.temperature_k).zone)
    water = D.effective_enthalpy(D.discharge(before, "water_mist", inp.cabin_volume_m3, inp.temperature_k,
                                             delivery_fraction=eta).zone)
    assert water == pytest.approx(co2, rel=1e-3)


def test_water_probability_follows_the_gates(monkeypatch):
    _with_gates(monkeypatch, water_allowed=False)
    r = A.advise(A.AdviceInput())
    assert r["agents"]["water_mist"]["thermal_estimate"] is None and r["agents"]["water_mist"]["withheld"]
    assert r["agents"]["co2"]["thermal_estimate"] is not None
    assert r["basis"] == "relative_only" and r["recommended_agent"] is None

    _with_gates(monkeypatch, water_allowed=True)
    r = A.advise(A.AdviceInput(delivery_fraction=1.0))
    assert r["agents"]["water_mist"]["thermal_estimate"] is not None
    assert r["basis"] == "thermal_model_comparison"


@pytest.mark.parametrize("fire_type", A.FIRE_TYPES)
def test_no_fire_type_returns_an_unsupported_number(monkeypatch, fire_type):
    _with_gates(monkeypatch, water_allowed=True)      # the most permissive gates
    seen = {}

    def fake_flex(features):
        seen["called"] = True
        return {"probabilities": {"Completion": 0.1, "Disruption": 0.1, "Extinction": 0.8},
                "applicability": {"in_domain": True}, "similar_tests": []}

    r = A.advise(A.AdviceInput(fire_type=fire_type), flex_predict=fake_flex)
    has_probabilities = any(r["agents"][a]["thermal_estimate"] or r["agents"][a]["flex_estimate"] for a in r["agents"])
    has_crossover = r["crossover_delivery_fraction"] is not None
    if fire_type in ("heptane", "methanol"):
        assert has_probabilities and has_crossover and "called" in seen
    elif fire_type == "other_liquid":
        assert not has_probabilities and has_crossover and "called" not in seen
    else:
        assert not has_probabilities and not has_crossover and "called" not in seen
        assert all(r["agents"][a]["effective_enthalpy_kcal_per_mol_o2"] is None for a in r["agents"])
    assert r["agents"]["co2"]["hazards"][0]["hazard"] == "cabin_ppco2"     # hazards for every type


def test_fire_type_decisions():
    assert A.advise(A.AdviceInput(fire_type="solid"))["outcome"] == "no_recommendation"
    battery = A.advise(A.AdviceInput(fire_type="electrical_battery"))
    assert battery["recommended_agent"] == "water_mist" and battery["basis"] == "sourced_rule"
    assert battery["decision_sources"] == [C.BATTERY_RULE["source"]]


def test_out_of_domain_atmosphere_withholds_the_probability(monkeypatch):
    _with_gates(monkeypatch, water_allowed=True)
    r = A.advise(A.AdviceInput(pressure_kpa=56.5, o2_fraction=0.34))   # exploration atmosphere, below FLEX pressures
    assert r["agents"]["co2"]["thermal_estimate"] is None
    assert any("pressure" in w for w in r["agents"]["co2"]["withheld"])
    assert r["recommended_agent"] is None


def test_invalid_advice_inputs_are_rejected():
    with pytest.raises(ValueError):
        A.advise(A.AdviceInput(fire_type="plasma"))
    with pytest.raises(ValueError):
        A.advise(A.AdviceInput(zone="somewhere"))
