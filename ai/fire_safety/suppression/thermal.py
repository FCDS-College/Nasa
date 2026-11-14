"""Thermal (effective-enthalpy) suppression model at runtime: JSON artefact executed with numpy.

P(extinction) = logistic(h_eff, ln p, fuel), fitted on the FLEX flight tests by ``calibrate.py``.
Because the only agent-dependent input is h_eff, the same model scores CO₂ and water mist on one scale;
that is what lets the advisor compare them (plan §3.3, D2).

The artefact's evaluation file holds the D2 gate results. ``gates()`` reads them, so whether an
absolute water-mist probability may be shown is never hand-set.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
ARTIFACT = ARTIFACT_DIR / "suppression_thermal_model.json"
EVALUATION = ARTIFACT_DIR / "suppression_thermal_evaluation.json"
FEATURES = ("h_eff_kj_per_mol_o2", "ln_pressure_atm", "heptane")
FUELS = ("Heptane", "Methanol")


def feature_vector(h_eff: float, pressure_atm: float, fuel: str) -> np.ndarray:
    return np.array([h_eff, float(np.log(pressure_atm)), 1.0 if fuel == "Heptane" else 0.0])


class ThermalModel:
    def __init__(self, artefact: dict, evaluation: dict | None = None):
        self.artefact = artefact
        self.evaluation = evaluation or {}
        p = artefact["logistic"]
        self._mean, self._scale = np.array(p["mean"]), np.array(p["scale"])
        self._coef, self._intercept = np.array(p["coef"]), float(p["intercept"])
        self.domain = artefact["domain"]

    @property
    def version(self) -> str:
        return self.artefact["model_version"]

    def p_extinction(self, h_eff: float, pressure_atm: float, fuel: str) -> float:
        z = (feature_vector(h_eff, pressure_atm, fuel) - self._mean) / self._scale
        return float(1.0 / (1.0 + np.exp(-(self._coef @ z + self._intercept))))

    def h50(self, pressure_atm: float, fuel: str) -> float:
        """h_eff at which P(extinction) = 0.5 (kJ/mol O₂)."""
        z_rest = (feature_vector(0.0, pressure_atm, fuel) - self._mean) / self._scale
        logit_rest = float(self._coef[1:] @ z_rest[1:]) + self._intercept
        return float(self._mean[0] - logit_rest * self._scale[0] / self._coef[0])

    def applicability(self, h_eff: float, pressure_atm: float, fuel: str) -> dict:
        reasons = []
        if fuel not in FUELS:
            reasons.append(f"fuel {fuel!r} was not flight-tested (FLEX: heptane, methanol)")
        lo, hi = self.domain["h_eff_kj_per_mol_o2"]["min"], self.domain["h_eff_kj_per_mol_o2"]["max"]
        if not lo <= h_eff <= hi:
            reasons.append(f"effective enthalpy {h_eff / 4.184:.1f} kcal/mol O₂ is outside the flight-tested range "
                           f"{lo / 4.184:.1f}–{hi / 4.184:.1f}")
        lo, hi = self.domain["pressure_atm"]["min"], self.domain["pressure_atm"]["max"]
        if not lo - 1e-9 <= pressure_atm <= hi + 1e-9:
            reasons.append(f"pressure {pressure_atm * 101.325:.1f} kPa is outside the flight-tested range "
                           f"{lo * 101.325:.1f}–{hi * 101.325:.1f} kPa")
        return {"in_domain": not reasons, "reasons": reasons}

    def gates(self) -> dict:
        g = self.evaluation.get("gates", {})
        flex_ok = bool(g.get("flex_auc", {}).get("passed"))
        mist_ok = bool(g.get("mist", {}).get("passed"))
        return {"flex_auc": g.get("flex_auc"), "mist": g.get("mist"), "water_probability_allowed": flex_ok and mist_ok,
                "model_signal_ok": flex_ok}


@lru_cache(maxsize=1)
def load() -> ThermalModel:
    artefact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    evaluation = json.loads(EVALUATION.read_text(encoding="utf-8")) if EVALUATION.exists() else None
    return ThermalModel(artefact, evaluation)
