"""FLEX outcome model at runtime: a JSON artefact executed with numpy only.

The artefact is produced by ``train_flex_outcome.py`` and committed with its evaluation report.
Two exported kinds are supported, so whichever candidate wins the grouped validation can ship:
``random_forest`` (trees as flat node arrays) and ``logistic_regression`` (standardize + softmax).

Applicability domain (strict, by design):
* every feature must lie inside the range seen in the 261 flight tests used for training;
* the query must be within the 95th-percentile nearest-neighbour distance of the training tests
  (standardized units), so a combination never flown together is flagged even when each value is.
Outside the domain the model returns no probabilities, only the reason.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "flex_outcome_model.json"


def export_forest(forest, classes: list[str]) -> list[dict]:
    """Flatten a fitted sklearn RandomForestClassifier into JSON-safe node arrays."""
    order = [list(forest.classes_).index(c) for c in classes]
    trees = []
    for estimator in forest.estimators_:
        t = estimator.tree_
        value = t.value[:, 0, :]
        value = value / value.sum(axis=1, keepdims=True)
        trees.append({
            "left": t.children_left.tolist(),
            "right": t.children_right.tolist(),
            "feature": t.feature.tolist(),
            "threshold": [float(x) for x in t.threshold],
            "value": [[float(v) for v in row[order]] for row in value],
        })
    return trees


def export_logistic(pipeline, classes: list[str]) -> dict:
    scaler, clf = pipeline.steps[0][1], pipeline.steps[-1][1]
    order = [list(clf.classes_).index(c) for c in classes]
    return {
        "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
        "coef": clf.coef_[order].tolist(), "intercept": clf.intercept_[order].tolist(),
    }


class FlexOutcomeModel:
    def __init__(self, artefact: dict):
        self.artefact = artefact
        self.kind = artefact["kind"]
        self.classes = artefact["classes"]
        self.features = artefact["features"]
        self.domain = artefact["domain"]
        if self.kind == "random_forest":
            self._trees = [
                (np.array(t["left"]), np.array(t["right"]), np.array(t["feature"]), np.array(t["threshold"]), np.array(t["value"]))
                for t in artefact["trees"]
            ]
        elif self.kind != "logistic_regression":
            raise ValueError(f"unsupported model kind {self.kind}")

    @property
    def version(self) -> str:
        return self.artefact["model_version"]

    def vector(self, features: dict[str, float]) -> np.ndarray:
        return np.array([float(features[f]) for f in self.features])

    def probabilities(self, features: dict[str, float]) -> np.ndarray:
        x = self.vector(features)
        if self.kind == "logistic_regression":
            p = self.artefact["logistic"]
            z = (x - np.array(p["mean"])) / np.array(p["scale"])
            logits = np.array(p["coef"]) @ z + np.array(p["intercept"])
            e = np.exp(logits - logits.max())
            return e / e.sum()
        total = np.zeros(len(self.classes))
        xf = x.astype(np.float32).astype(float)   # sklearn compares in float32
        for left, right, feature, threshold, value in self._trees:
            node = 0
            while left[node] != -1:
                node = left[node] if xf[feature[node]] <= threshold[node] else right[node]
            total += value[node]
        return total / len(self._trees)

    def standardized(self, x: np.ndarray) -> np.ndarray:
        return (x - np.array(self.domain["scaler_mean"])) / np.array(self.domain["scaler_scale"])

    def applicability(self, features: dict[str, float], nearest_distance: float | None) -> dict:
        checks = []
        for name in self.features:
            if name == "heptane":
                continue
            lo, hi = self.domain["feature_ranges"][name]["min"], self.domain["feature_ranges"][name]["max"]
            value = float(features[name])
            ok = lo - 1e-12 <= value <= hi + 1e-12
            checks.append({"feature": name, "label": self.artefact["feature_labels"][name], "value": round(value, 6),
                           "trained_min": round(lo, 6), "trained_max": round(hi, 6), "inside": ok})
        limit = self.domain["max_nearest_neighbour_distance"]
        combo_ok = nearest_distance is not None and nearest_distance <= limit
        in_domain = all(c["inside"] for c in checks) and combo_ok
        reasons = [_outside(c) for c in checks if not c["inside"]]
        if not combo_ok:
            reasons.append("this combination of conditions is farther from every flight test than 95% of tests are from their "
                           "nearest neighbour")
        return {"in_domain": in_domain, "checks": checks, "nearest_test_distance": None if nearest_distance is None else round(nearest_distance, 4),
                "max_distance": limit, "reasons": reasons}


def _outside(check: dict) -> str:
    """Readable refusal reason; pressures are shown in kPa, which is how the dashboard asks for them."""
    if check["feature"] in {"pressure_atm", "ppo2_atm"}:
        f = 101.325
        name = "pressure" if check["feature"] == "pressure_atm" else "O₂ partial pressure"
        return (f"{name} {check['value'] * f:.1f} kPa is outside the flight-tested range "
                f"{check['trained_min'] * f:.1f}–{check['trained_max'] * f:.1f} kPa")
    return (f"{check['label']} {check['value']:.3g} is outside the flight-tested range "
            f"{check['trained_min']:.3g}–{check['trained_max']:.3g}")


@lru_cache(maxsize=1)
def load(path: str | None = None) -> FlexOutcomeModel:
    return FlexOutcomeModel(json.loads(Path(path or ARTIFACT).read_text(encoding="utf-8")))
