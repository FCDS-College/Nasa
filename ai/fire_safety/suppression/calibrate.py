"""Calibrate the thermal suppression model on FLEX and evaluate the D2 gates.

    python -m ai.fire_safety.suppression.calibrate            # writes artifacts/suppression_thermal_*.json
    python -m ai.fire_safety.suppression.calibrate --check    # recompute and fail if the artefacts differ

Model: binary logistic regression, P(Extinction) from effective enthalpy per mol O₂ (h_eff),
ln(pressure) and fuel, on the same 261 usable FLEX tests as the outcome model. Unweighted, so the
probabilities stay calibrated: the advisor compares them across agents.

Gates (plan D2, decided 2026-11-14):
1. flex_auc: 5× repeated grouped-by-test-day 5-fold CV extinction ROC-AUC, mean − 1 SD ≥ 0.75.
2. mist: on the MIST (STS-107) lean propane–air cases the model must be *conservative*: the water
   loading at which it predicts P(extinction) = 0.5 must be at least the highest measured
   extinguishing loading (4.8 % at 30 µm). MIST is never used to fit anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ai.fire_safety import flex
from ai.fire_safety.suppression import constants as C
from ai.fire_safety.suppression import discharge as D
from ai.fire_safety.suppression import thermal as T

SEED = 2026
MODEL_VERSION = "suppression-thermal-logistic-1.0.0"
MIST_FUEL_PROXY = "Heptane"   # MIST burned propane; heptane is the flight-tested hydrocarbon


def dataset():
    tests = [t for t in flex.load_table() if t.features is not None and t.outcome is not None and t.test_date]
    X, y, groups = [], [], []
    for t in tests:
        f = t.features
        atm = D.cabin(f["pressure_atm"] * 101.325, f["o2"], f["co2"], f["he"])
        X.append(T.feature_vector(D.effective_enthalpy(atm), f["pressure_atm"], t.fuel))
        y.append(1 if t.outcome == "Extinction" else 0)
        groups.append(t.test_date)
    return np.array(X), np.array(y), np.array(groups)


def make():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, C=1.0))


def grouped_folds(groups, seed, n_splits=5):
    order = np.random.default_rng(seed).permutation(np.unique(groups))
    fold_of_group = {g: i % n_splits for i, g in enumerate(order)}
    fold = np.array([fold_of_group[g] for g in groups])
    return [(np.where(fold != k)[0], np.where(fold == k)[0]) for k in range(n_splits)]


def repeated_cv(X, y, groups, columns, repeats=5):
    aucs, briers = [], []
    for r in range(repeats):
        p = np.zeros(len(y))
        for train, test in grouped_folds(groups, SEED + r):
            m = make().fit(X[train][:, columns], y[train])
            p[test] = m.predict_proba(X[test][:, columns])[:, 1]
        aucs.append(roc_auc_score(y, p))
        briers.append(brier_score_loss(y, p))
    return {"extinction_roc_auc": {"mean": round(float(np.mean(aucs)), 4), "sd": round(float(np.std(aucs)), 4)},
            "extinction_brier": {"mean": round(float(np.mean(briers)), 4), "sd": round(float(np.std(briers)), 4)}}


def export(pipeline) -> dict:
    scaler, clf = pipeline.steps[0][1], pipeline.steps[-1][1]
    return {"mean": [round(float(v), 10) for v in scaler.mean_], "scale": [round(float(v), 10) for v in scaler.scale_],
            "coef": [round(float(v), 10) for v in clf.coef_[0]], "intercept": round(float(clf.intercept_[0]), 10)}


def mist_check(model: T.ThermalModel) -> dict:
    def p_at(omega):
        return model.p_extinction(D.effective_enthalpy(D.mist_atmosphere(omega)), 1.0, MIST_FUEL_PROXY)

    lo, hi = 0.0, 1.0
    if p_at(hi) < 0.5:
        omega_star = None          # never predicts extinction: maximally conservative
    elif p_at(lo) >= 0.5:
        omega_star = 0.0
    else:
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if p_at(mid) < 0.5 else (lo, mid)
        omega_star = hi
    required = max(c["omega_w_extinguished"] for c in C.MIST_EXTINCTION)
    cases = [{"cmd_um": c["cmd_um"],
              "measured_extinction_omega_w": c["omega_w_extinguished"],
              "model_p_extinction_at_measured_extinction": round(p_at(c["omega_w_extinguished"]), 4),
              "measured_no_extinction_omega_w": c["omega_w_not_extinguished"],
              "model_p_extinction_at_no_extinction": round(p_at(c["omega_w_not_extinguished"]), 4),
              "under_prediction_factor": None if omega_star is None else round(omega_star / c["omega_w_extinguished"], 3)}
             for c in C.MIST_EXTINCTION]
    passed = omega_star is None or omega_star >= required
    return {"passed": bool(passed), "rule": f"model ω_w at P=0.5 must be ≥ {required} (highest measured extinguishing loading)",
            "model_omega_w_at_p50": None if omega_star is None else round(omega_star, 5),
            "fuel_proxy": MIST_FUEL_PROXY, "cases": cases,
            "note": "MIST burned premixed propane–air at 1 atm in a 6.3 cm tube; heptane is used as the hydrocarbon proxy."}


def run() -> tuple[dict, dict]:
    X, y, groups = dataset()
    cv = repeated_cv(X, y, groups, [0, 1, 2])
    cv_h_only = repeated_cv(X, y, groups, [0])
    final = make().fit(X, y)
    h, p_atm = X[:, 0], np.exp(X[:, 1])
    artefact = {
        "model_version": MODEL_VERSION,
        "kind": "logistic_regression_binary",
        "features": list(T.FEATURES),
        "target": "Extinction (1) vs Disruption or Completion (0)",
        "logistic": export(final),
        "domain": {"h_eff_kj_per_mol_o2": {"min": round(float(h.min()), 6), "max": round(float(h.max()), 6)},
                   "pressure_atm": {"min": round(float(p_atm.min()), 6), "max": round(float(p_atm.max()), 6)}},
        "training_rows": int(len(y)),
        "flex_table_sha256": hashlib.sha256(flex.FLEX_TABLE.read_bytes()).hexdigest(),
    }
    model = T.ThermalModel(artefact)
    auc = cv["extinction_roc_auc"]
    lower = round(auc["mean"] - auc["sd"], 4)
    evaluation = {
        "model_version": MODEL_VERSION,
        "training_data": {"rows_used": int(len(y)), "extinction": int(y.sum()), "test_days": int(len(np.unique(groups)))},
        "repeated_grouped_cv": cv,
        "repeated_grouped_cv_h_eff_only": cv_h_only,
        "comparison": "FLEX outcome model (7 inputs) extinction ROC-AUC 0.857 ± 0.010, docs/evaluation/reports/flex-outcome-model.md",
        "h50_kcal_per_mol_o2_at_1_atm": {fuel: round(model.h50(1.0, fuel) / C.KJ_PER_KCAL, 2) for fuel in T.FUELS},
        "literature_check": {"normal_gravity_pmma_kcal_per_mol_o2": C.LITERATURE_H_EFF_KCAL_PER_MOL_O2,
                             "air_kcal_per_mol_o2": round(D.effective_enthalpy(D.cabin(101.325, 0.21)) / C.KJ_PER_KCAL, 2),
                             "source": "NTRS 20040161262 p. 362; not used for fitting"},
        "gates": {
            "flex_auc": {"passed": bool(lower >= C.GATE_FLEX_AUC_LOWER_BOUND), "lower_bound": lower,
                         "threshold": C.GATE_FLEX_AUC_LOWER_BOUND, "rule": "mean − 1 SD of repeated grouped-CV ROC-AUC"},
            "mist": mist_check(model),
        },
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    return artefact, evaluation


def _comparable(evaluation: dict) -> dict:
    return {k: v for k, v in evaluation.items() if k != "generated_at"}


def is_current() -> bool:
    artefact, evaluation = run()
    current_a = json.loads(T.ARTIFACT.read_text(encoding="utf-8"))
    current_e = json.loads(T.EVALUATION.read_text(encoding="utf-8"))
    return (current_a == json.loads(json.dumps(artefact))
            and _comparable(current_e) == _comparable(json.loads(json.dumps(evaluation))))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the committed artefacts are out of date")
    args = parser.parse_args(argv)
    if args.check:
        same = is_current()
        print("artefact current" if same else "artefact OUT OF DATE: rerun without --check")
        return 0 if same else 1
    artefact, evaluation = run()
    T.ARTIFACT.write_text(json.dumps(artefact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    T.EVALUATION.write_text(json.dumps(evaluation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    g = evaluation["gates"]
    print(f"CV ROC-AUC {evaluation['repeated_grouped_cv']['extinction_roc_auc']} lower bound {g['flex_auc']['lower_bound']} "
          f"-> flex gate {'PASS' if g['flex_auc']['passed'] else 'FAIL'}; mist gate {'PASS' if g['mist']['passed'] else 'FAIL'} "
          f"(model omega* {g['mist']['model_omega_w_at_p50']}); h50 {evaluation['h50_kcal_per_mol_o2_at_1_atm']} kcal/mol O2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
