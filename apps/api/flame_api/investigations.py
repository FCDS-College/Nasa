"""Fire-safety dashboard API: investigation summaries, scenario ranking, insights, FLEX outcome model.

    GET /api/investigations                 every investigation, ranked for a cabin atmosphere
    GET /api/investigations/{id}            one investigation: NASA's own summary sections + data envelope
    GET /api/insights                       computed, cited fire-safety statements for a cabin atmosphere
    GET /api/insights/flex-outcome          FLEX outcome model: probabilities, applicability, similar flight tests
    GET /api/scenarios/{id}/history         a historical scenario's cited story, timeline and data-covered alternative

All read-only and deterministic. Numbers come from ingested flight-test rows (ai.fire_safety); text
summaries are NASA's ISA-Tab metadata, verbatim and cited. Nothing here calls a language model.
"""
from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, Depends, Path as ApiPath, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ai.fire_safety import flex, investigations as analytics, model as outcome_model, scenarios
from flame_api.contracts import error_body, response_meta
from flame_api.database import get_session
from flame_api.ingest import ISATAB_PARSER_VERSION
from flame_api.knowledge_version import current_knowledge_version
from flame_api.models import DocumentRecord, EvidenceRecord, ExperimentCondition, ExperimentRecord, SourceRecord
from flame_api.registry import read_registry

router = APIRouter()
INVESTIGATION_ID_PATTERN = r"^FF-[A-Z0-9][A-Z0-9-]{1,40}$"
EVALUATION_REPORT = Path(outcome_model.ARTIFACT).with_name("flex_outcome_evaluation.json")
# Named in the challenge statement (BASS, Saffire, SAME, FLEX, ACME) but not in our registry yet. Empty since
# 2026-11-13: every PSI combustion investigation the challenge's resources page lists is registered (SAME = FF-PSI-102).
CHALLENGE_NOT_ACQUIRED: tuple[dict, ...] = ()
SUMMARY_SECTIONS = ("Objective", "Hypothesis", "Approach", "Research impacts")
_cache_lock = Lock()
_cache: dict[str, tuple] = {}


def _source(source: SourceRecord) -> dict:
    return {"source_id": source.source_id, "title": source.title, "short_name": source.short_name, "repository": source.repository,
            "persistent_identifier": source.persistent_identifier, "license": source.license, "access_url": source.access_url}


def _load(session: Session) -> tuple[dict, dict, dict, dict, set[str]]:
    """(registry rows, canonical tests by source, ISA-Tab docs by source, sources, gravity regimes), cached per knowledge version."""
    # Cached per published knowledge version and row counts, so a re-ingest is picked up without a restart.
    key = f"{current_knowledge_version(session)}:{session.query(ExperimentRecord).count()}:{session.query(DocumentRecord).count()}"
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    registry = {r["source_id"]: r for r in read_registry() if r.get("source_type") == "investigation_dataset"}
    sources = {s.source_id: s for s in session.query(SourceRecord).filter(SourceRecord.source_id.in_(list(registry)))}
    experiments = session.query(ExperimentRecord.experiment_id, ExperimentRecord.source_id, ExperimentRecord.test_id,
                                ExperimentRecord.fuel_or_material, ExperimentRecord.gravity_regime) \
        .filter(ExperimentRecord.source_id.in_(list(registry))).all()
    rows: dict[str, analytics.TestRow] = {}
    regimes: set[str] = set()
    for experiment_id, source_id, test_id, fuel, gravity in experiments:
        rows[experiment_id] = analytics.TestRow(source_id, experiment_id, test_id, fuel, {})
        regimes.add(gravity)
    for experiment_id, variable, numeric, text, si, evidence_id in session.query(
        ExperimentCondition.experiment_id, ExperimentCondition.variable, ExperimentCondition.value_numeric,
        ExperimentCondition.value_text, ExperimentCondition.value_si, ExperimentCondition.evidence_id,
    ).filter(ExperimentCondition.experiment_id.in_(list(rows))).yield_per(5000):
        rows[experiment_id].conditions[variable] = analytics.Condition(numeric, text, si, evidence_id)
    by_source: dict[str, list[analytics.Canonical]] = defaultdict(list)
    for row in sorted(rows.values(), key=lambda r: (r.source_id, r.test_id, r.experiment_id)):
        by_source[row.source_id].append(analytics.canonical(row))
    isatab: dict[str, dict] = {}
    for document in session.query(DocumentRecord).filter(DocumentRecord.parser_version == ISATAB_PARSER_VERSION):
        sections = {}
        for e in session.query(EvidenceRecord).filter(EvidenceRecord.document_id == document.document_id):
            label = (e.locator or {}).get("label")
            text = e.excerpt or ""
            source = sources.get(document.source_id)
            prefix = f"{(source.short_name or source.title) if source else ''} {str(label).lower()}: "
            sections[label] = {"text": text[len(prefix):] if text.startswith(prefix) else text, "evidence_id": e.evidence_id}
        isatab[document.source_id] = {"document_id": document.document_id, "fields": (document.payload or {}).get("isatab", {}),
                                      "sections": sections}
    result = (registry, dict(by_source), isatab, sources, regimes)
    with _cache_lock:
        _cache.clear()
        _cache[key] = result
    return result


def reset_cache() -> None:
    with _cache_lock:
        _cache.clear()


Gravity = Literal["microgravity", "lunar", "martian", "earth"]


def _scenario(request: Request, scenario: str | None, o2_fraction: float | None, pressure_kpa: float | None,
              gravity: str | None = None):
    if o2_fraction is not None or pressure_kpa is not None:
        if o2_fraction is None or pressure_kpa is None:
            return None, _bad(request, "o2_fraction", "o2_fraction and pressure_kpa must be given together")
        return scenarios.custom(o2_fraction, pressure_kpa, gravity or scenarios.FLIGHT_GRAVITY), None
    if gravity is not None:
        return None, _bad(request, "gravity", "gravity applies to a custom atmosphere (o2_fraction and pressure_kpa)")
    chosen = scenarios.BY_ID.get(scenario or "iss_nominal")
    if chosen is None:
        return None, _bad(request, "scenario", f"unknown scenario; use one of {', '.join(scenarios.BY_ID)}")
    return chosen, None


def _bad(request: Request, field: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=400, content=error_body(request, "VALIDATION_ERROR", "Request validation failed.",
                                                            field_errors=[{"field": field, "message": message}]))


def _status(source_id: str, tests: list) -> str:
    return "ingested" if tests else "metadata_only"


def _summary(registry_row: dict, isatab_doc: dict | None, sources: dict, tests: list, scenario) -> dict:
    sid = registry_row["source_id"]
    env = analytics.envelope(tests)
    fields = (isatab_doc or {}).get("fields", {})
    sections = (isatab_doc or {}).get("sections", {})
    item = {
        "investigation_id": sid,
        "acronym": registry_row.get("short_name"),
        "title": registry_row.get("title"),
        "status": _status(sid, tests),
        "flight_platform": registry_row.get("flight_platform"),
        "hardware": (sections.get("Experiment hardware") or {}).get("text"),
        "dates": registry_row.get("source_date_range") or (
            f"{fields.get('start_date')} to {fields.get('end_date')}" if fields.get("start_date") else None),
        "persistent_identifier": registry_row.get("persistent_identifier"),
        "license": registry_row.get("license"),
        "access_url": registry_row.get("access_url"),
        "source": _source(sources[sid]) if sid in sources else None,
        "fire_safety_use": registry_row.get("primary_fire_safety_use") or [],
        "key_variables": registry_row.get("key_variables") or [],
        "key_outputs": registry_row.get("key_outputs") or [],
        "objective": sections.get("Objective"),
        "data": env,
        "coverage_note": _coverage(registry_row),
        "relevance": analytics.relevance(tests, env, scenario) if tests else None,
    }
    return item


def _coverage(row: dict) -> str | None:
    known = row.get("known_file_count")
    size = row.get("known_size")
    if not known:
        return None
    return (f"Flame holds this investigation's published experimental table and metadata; the full NASA PSI release has "
            f"{known} files ({size}). Results describe the table, not every raw file.")


@router.get("/api/investigations", tags=["Fire safety"])
def list_investigations(
    request: Request,
    scenario: Annotated[str | None, Query(max_length=40)] = None,
    o2_fraction: Annotated[float | None, Query(ge=0.05, le=1.0)] = None,
    pressure_kpa: Annotated[float | None, Query(ge=5.0, le=400.0)] = None,
    gravity: Gravity | None = None,
    session: Session = Depends(get_session),
):
    chosen, error = _scenario(request, scenario, o2_fraction, pressure_kpa, gravity)
    if error:
        return error
    registry, by_source, isatab, sources, regimes = _load(session)
    items = [_summary(row, isatab.get(sid), sources, by_source.get(sid, []), chosen)
             for sid, row in registry.items() if sid != "FF-PSI-DSI" and (row.get("domain") or "combustion") != "non_combustion"
             and row.get("experiment_family") != "DECLIC-DSI"]
    ranked = analytics.rank(items)
    return {
        "scenario": chosen.as_dict(),
        "scenarios": [s.as_dict() for s in scenarios.SCENARIOS],
        "ranking_method": analytics.FORMULA,
        "coverage": analytics.coverage({sid: ts for sid, ts in by_source.items() if sid in {i["investigation_id"] for i in ranked}},
                                       chosen, _flight_regimes(regimes)),
        "items": ranked,
        "not_acquired": list(CHALLENGE_NOT_ACQUIRED),
        "totals": {"investigations": len(ranked), "with_data": sum(1 for i in ranked if i["status"] == "ingested"),
                   "flight_tests": sum(i["data"]["tests"] for i in ranked)},
        "meta": response_meta(request),
    }


@router.get("/api/investigations/{investigation_id}", tags=["Fire safety"])
def get_investigation(
    request: Request,
    investigation_id: Annotated[str, ApiPath(pattern=INVESTIGATION_ID_PATTERN)],
    scenario: Annotated[str | None, Query(max_length=40)] = None,
    o2_fraction: Annotated[float | None, Query(ge=0.05, le=1.0)] = None,
    pressure_kpa: Annotated[float | None, Query(ge=5.0, le=400.0)] = None,
    gravity: Gravity | None = None,
    session: Session = Depends(get_session),
):
    chosen, error = _scenario(request, scenario, o2_fraction, pressure_kpa, gravity)
    if error:
        return error
    registry, by_source, isatab, sources, regimes = _load(session)
    row = registry.get(investigation_id)
    if row is None or row.get("experiment_family") == "DECLIC-DSI":
        return JSONResponse(status_code=404, content=error_body(
            request, "INVESTIGATION_NOT_FOUND", "Investigation was not found.", details={"investigation_id": investigation_id}))
    tests = by_source.get(investigation_id, [])
    item = _summary(row, isatab.get(investigation_id), sources, tests, chosen)
    doc = isatab.get(investigation_id) or {}
    item["summary_sections"] = [{"heading": h, **doc["sections"][h]} for h in SUMMARY_SECTIONS if h in doc.get("sections", {})]
    item["publications"] = (doc.get("fields") or {}).get("publications", [])
    item["metadata_document_id"] = doc.get("document_id")
    item["insights"] = [i for i in analytics.insights({investigation_id: tests}, chosen, _names(registry), None, regimes)
                        if investigation_id in i["investigations"] and i["insight_id"] != "coverage_gaps"]
    item["sample_tests"] = [_test_ref(t) for t in tests[:10]]
    return {"investigation": item, "scenario": chosen.as_dict(), "meta": response_meta(request)}


def _flight_regimes(regimes: set[str]) -> list[str]:
    """Gravity regimes recorded for the flight tests; 'unknown' rows say nothing about gravity."""
    return sorted(r for r in regimes if r and r != "unknown") or [scenarios.FLIGHT_GRAVITY]


def _names(registry: dict) -> dict[str, str]:
    return {sid: (r.get("short_name") or sid) for sid, r in registry.items()}


def _test_ref(t: analytics.Canonical) -> dict:
    return {"experiment_id": t.row.experiment_id, "test_id": t.row.test_id, "fuel_or_material": t.material,
            "o2_fraction": t.o2, "pressure_kpa": None if t.pressure_kpa is None else round(t.pressure_kpa, 2),
            "flow_velocity_m_s": t.flow_m_s, "end_state": t.end_state, "duration_s": t.duration_s,
            "end_state_evidence_id": t.evidence("test_end")}


@router.get("/api/insights", tags=["Fire safety"])
def list_insights(
    request: Request,
    scenario: Annotated[str | None, Query(max_length=40)] = None,
    o2_fraction: Annotated[float | None, Query(ge=0.05, le=1.0)] = None,
    pressure_kpa: Annotated[float | None, Query(ge=5.0, le=400.0)] = None,
    gravity: Gravity | None = None,
    session: Session = Depends(get_session),
):
    chosen, error = _scenario(request, scenario, o2_fraction, pressure_kpa, gravity)
    if error:
        return error
    registry, by_source, _, _, regimes = _load(session)
    estimate = _scenario_model_insight(by_source.get("FF-PSI-69", []), chosen, _flight_regimes(regimes))
    items = analytics.insights(by_source, chosen, _names(registry), estimate, regimes)
    return {"scenario": chosen.as_dict(), "items": items, "meta": response_meta(request)}


# ------------------------------------------------------------------------------------------ FLEX model

@lru_cache(maxsize=1)
def _evaluation_summary() -> dict:
    report = json.loads(EVALUATION_REPORT.read_text(encoding="utf-8"))
    selected = report["selected_model"]
    rep = report["repeated_grouped_cv_all_rows"]
    return {
        "model_version": report["model_version"],
        "model_kind": selected,
        "training_rows": report["training_data"]["rows_used"],
        "test_days": report["training_data"]["test_days"],
        "class_counts": report["training_data"]["class_counts"],
        "primary_estimate": {"method": "5x repeated 5-fold CV grouped by test day, all usable rows",
                             "macro_f1": rep[selected]["macro_f1"], "balanced_accuracy": rep[selected]["balanced_accuracy"],
                             "extinction_roc_auc": rep[selected]["extinction_roc_auc"],
                             "majority_baseline_macro_f1": rep["majority_class"]["macro_f1"]},
        "holdout": {k: report["holdout"][selected][k] for k in ("macro_f1", "balanced_accuracy", "extinction_roc_auc", "accuracy")},
        "holdout_note": report["protocol_history"][-1],
        "feature_importance": report["permutation_importance_final_model"],
        "report": "docs/evaluation/reports/flex-outcome-model.md",
    }


def _flex_training(tests: list[analytics.Canonical], model: outcome_model.FlexOutcomeModel):
    """Training-equivalent features for every FLEX test, from the ingested rows (same rules as training)."""
    out = []
    for t in tests:
        conditions = {v: (c.numeric, c.text) for v, c in t.row.conditions.items()}
        ft = flex.from_conditions(t.row.test_id, t.row.fuel, conditions)
        if ft.features is not None and ft.outcome is not None and ft.test_date:   # the training set's rows exactly
            out.append((t, ft.features, model.standardized(model.vector(ft.features))))
    return out


def predict(features: dict[str, float], tests: list[analytics.Canonical], k: int = 8) -> dict:
    model = outcome_model.load()
    training = _flex_training(tests, model)
    z = model.standardized(model.vector(features))
    distances = sorted(((float(np.sqrt(((zt - z) ** 2).sum())), t, f) for t, f, zt in training), key=lambda r: r[0])
    nearest = distances[0][0] if distances else None
    applicability = model.applicability(features, nearest)
    probabilities = None
    if applicability["in_domain"]:
        p = model.probabilities(features)
        probabilities = {c: round(float(v), 4) for c, v in zip(model.classes, p)}
    similar = [{**_test_ref(t), "distance": round(d, 3), "droplet_diameter_mm": f["d0_mm"],
                "co2_fraction": f["co2"], "he_fraction": f["he"]} for d, t, f in distances[:k]]
    near_ends = [s["end_state"] for s in similar]
    return {
        "probabilities": probabilities,
        "predicted_end_state": max(probabilities, key=probabilities.get) if probabilities else None,
        "applicability": applicability,
        "similar_tests": similar,
        "similar_tests_end_states": {e: near_ends.count(e) for e in sorted(set(near_ends))},
    }


def _features(fuel: str, o2: float, pressure_kpa: float, co2: float, he: float, d0: float) -> dict[str, float]:
    p_atm = pressure_kpa / flex.KPA_PER_ATM
    return {"o2": o2, "pressure_atm": p_atm, "ppo2_atm": o2 * p_atm, "co2": co2, "he": he, "d0_mm": d0,
            "heptane": 1.0 if fuel == "Heptane" else 0.0}


def _sweep_grid(lo: float, hi: float, requested: float | None) -> list[float]:
    """12 points over the trained O2 range, extended (out of domain) to reach a requested O2 outside it,
    so the chart can show how far beyond the flight data an atmosphere such as Apollo 1's pure oxygen lies."""
    grid = [float(x) for x in np.round(np.linspace(lo, hi, 12), 4)]
    if requested is not None and requested > hi + 1e-9:
        grid += [float(x) for x in np.round(np.linspace(hi, min(requested, 1.0), 7)[1:], 4)]
    if requested is not None and requested < lo - 1e-9:
        grid = [float(x) for x in np.round(np.linspace(max(requested, 0.0), lo, 4)[:-1], 4)] + grid
    return grid


def _sweep(fuel, pressure_kpa, co2, he, d0, tests, requested_o2: float | None = None) -> list[dict]:
    model = outcome_model.load()
    lo, hi = model.domain["feature_ranges"]["o2"]["min"], model.domain["feature_ranges"]["o2"]["max"]
    training = _flex_training(tests, model)
    points = []
    for o2 in _sweep_grid(lo, hi, requested_o2):
        f = _features(fuel, float(o2), pressure_kpa, co2, he, d0)
        z = model.standardized(model.vector(f))
        nearest = min((float(np.sqrt(((zt - z) ** 2).sum())) for _, _, zt in training), default=None)
        app = model.applicability(f, nearest)
        p = model.probabilities(f) if app["in_domain"] else None
        points.append({"o2_fraction": float(o2), "in_domain": app["in_domain"],
                       "probabilities": None if p is None else {c: round(float(v), 4) for c, v in zip(model.classes, p)}})
    return points


@router.get("/api/insights/flex-outcome", tags=["Fire safety"])
def flex_outcome(
    request: Request,
    fuel: Literal["Heptane", "Methanol"] = "Heptane",
    o2_fraction: Annotated[float, Query(ge=0.05, le=1.0)] = 0.21,
    pressure_kpa: Annotated[float, Query(ge=5.0, le=400.0)] = 101.3,
    co2_fraction: Annotated[float, Query(ge=0.0, le=0.9)] = 0.0,
    he_fraction: Annotated[float, Query(ge=0.0, le=0.9)] = 0.0,
    droplet_diameter_mm: Annotated[float, Query(gt=0.0, le=20.0)] = 3.0,
    session: Session = Depends(get_session),
):
    if o2_fraction + co2_fraction + he_fraction > 1.0 + 1e-9:
        return _bad(request, "o2_fraction", "o2_fraction + co2_fraction + he_fraction cannot exceed 1")
    _, by_source, _, _, _ = _load(session)
    tests = by_source.get("FF-PSI-69", [])
    features = _features(fuel, o2_fraction, pressure_kpa, co2_fraction, he_fraction, droplet_diameter_mm)
    result = predict(features, tests)
    return {
        "input": {"fuel": fuel, "o2_fraction": o2_fraction, "pressure_kpa": pressure_kpa, "co2_fraction": co2_fraction,
                  "he_fraction": he_fraction, "droplet_diameter_mm": droplet_diameter_mm},
        **result,
        "o2_sweep": _sweep(fuel, pressure_kpa, co2_fraction, he_fraction, droplet_diameter_mm, tests, o2_fraction),
        "model": _evaluation_summary(),
        "claim_class": "estimated",
        "scope": ("Estimated from 261 FLEX droplet tests (methanol, heptane) in microgravity. It does not describe solid "
                  "materials, other fuels, partial gravity or flame temperature."),
        "meta": response_meta(request),
    }


def _gravity_reason(scenario, flight_regimes: list[str]) -> str | None:
    if scenario.gravity in flight_regimes:
        return None
    where = "1 g (Earth)" if scenario.gravity == "earth" else f"{scenario.gravity} gravity"
    return f"every FLEX test was flown in {' and '.join(flight_regimes)}; this atmosphere is at {where}"


def _scenario_model_insight(tests: list[analytics.Canonical], scenario, flight_regimes: list[str] | None = None) -> dict | None:
    if not tests:
        return None
    model = outcome_model.load()
    d0 = float(np.median([f["d0_mm"] for _, f, _ in _flex_training(tests, model)]))
    gravity_reason = _gravity_reason(scenario, flight_regimes or [scenarios.FLIGHT_GRAVITY])
    rows = {}
    for fuel in flex.FUELS:
        rows[fuel] = predict(_features(fuel, scenario.o2_fraction, scenario.pressure_kpa, 0.0, 0.0, d0), tests, k=5)
        if gravity_reason:   # the model has no gravity input: a regime nobody flew is outside its domain
            app = rows[fuel]["applicability"]
            rows[fuel].update(probabilities=None, predicted_end_state=None,
                              applicability={**app, "in_domain": False, "reasons": [*app["reasons"], gravity_reason]})
    in_domain = {f: r["applicability"]["in_domain"] for f, r in rows.items()}
    parts = []
    for fuel, r in rows.items():
        if r["probabilities"]:
            share = r["probabilities"]["Extinction"]
            parts.append(f"{fuel.lower()}: {'<1' if share < 0.005 else round(100 * share)}% chance the flame self-extinguishes")
        else:
            parts.append(f"{fuel.lower()}: no estimate ({'; '.join(r['applicability']['reasons'])})")
    evidence = []
    for r in rows.values():
        evidence += [{"evidence_id": s["end_state_evidence_id"], "experiment_id": s["experiment_id"], "test_id": s["test_id"]}
                     for s in r["similar_tests"][:3] if s["end_state_evidence_id"]]
    return {
        "insight_id": "flex_model_scenario_estimate",
        "title": "Outcome model estimate for this atmosphere",
        "kind": "model_estimate" if any(in_domain.values()) else "coverage_gap",
        "investigations": ["FF-PSI-69"],
        "statement": (f"For a {d0:.2f} mm droplet with no added diluent at {scenario.o2_fraction:.2f} O₂ and "
                      f"{scenario.pressure_kpa:.1f} kPa, the FLEX outcome model gives " + "; ".join(parts) + "."),
        "numbers": {f: {"probabilities": r["probabilities"], "in_domain": r["applicability"]["in_domain"]} for f, r in rows.items()},
        "evidence": evidence,
        "caveats": [f"Model {outcome_model.load().version}: macro-F1 "
                    f"{_evaluation_summary()['primary_estimate']['macro_f1']['mean']:.2f} (baseline "
                    f"{_evaluation_summary()['primary_estimate']['majority_baseline_macro_f1']['mean']:.2f}), extinction ROC-AUC "
                    f"{_evaluation_summary()['primary_estimate']['extinction_roc_auc']['mean']:.2f}; droplets only.",
                    "Evidence lists the nearest real flight tests and their recorded end state."],
    }



# ------------------------------------------------------------------------------------- historical scenarios

SCENARIO_ID_PATTERN = r"^[a-z0-9_]{3,40}$"


def _page_evidence(session: Session, source_ids: set[str]) -> dict[tuple[str, int], str]:
    """(source_id, page) -> evidence_id for the ingested pages of these reports."""
    out: dict[tuple[str, int], str] = {}
    for evidence_id, source_id, locator in session.query(EvidenceRecord.evidence_id, EvidenceRecord.source_id,
                                                         EvidenceRecord.locator) \
            .filter(EvidenceRecord.source_id.in_(sorted(source_ids))):
        if isinstance(locator, dict) and locator.get("type") == "page" and isinstance(locator.get("page"), int):
            out.setdefault((source_id, locator["page"]), evidence_id)
    return out


def _cite(source: dict, registry: dict[str, dict], pages: dict[tuple[str, int], str]) -> dict:
    row = registry.get(source["source_id"], {})
    return {"source_id": source["source_id"], "page": source["page"], "quote": source.get("quote"),
            "title": row.get("title"), "short_name": row.get("short_name"), "access_url": row.get("access_url"),
            "evidence_id": pages.get((source["source_id"], source["page"]))}


@router.get("/api/scenarios/{scenario_id}/history", tags=["Fire safety"])
def scenario_history(
    request: Request,
    scenario_id: Annotated[str, ApiPath(pattern=SCENARIO_ID_PATTERN)],
    session: Session = Depends(get_session),
):
    """A historical atmosphere's story, page-cited timeline, lesson and the data-covered alternative to show next."""
    history = scenarios.HISTORIES.get(scenario_id)
    if history is None:
        return JSONResponse(status_code=404, content=error_body(
            request, "SCENARIO_HISTORY_NOT_FOUND", "No history is published for this scenario.",
            details={"scenario_id": scenario_id, "historical_scenarios": sorted(scenarios.HISTORIES)}))
    cited = {s["source_id"] for s in history.lesson_sources} | {s["source_id"] for s in history.alternative["sources"]} \
        | {s["source_id"] for e in history.timeline for s in e["sources"]}
    registry = {r["source_id"]: r for r in read_registry() if r["source_id"] in cited}
    pages = _page_evidence(session, cited)
    alternative = scenarios.BY_ID[history.alternative["scenario_id"]]
    return {
        "scenario": scenarios.BY_ID[scenario_id].as_dict(),
        "year": history.year,
        "story": history.story,
        "lesson": history.lesson,
        "lesson_sources": [_cite(s, registry, pages) for s in history.lesson_sources],
        "timeline": [{"date": e["date"], "title": e["title"], "text": e["text"],
                      "sources": [_cite(s, registry, pages) for s in e["sources"]]} for e in history.timeline],
        "alternative": {"scenario": alternative.as_dict(), "headline": history.alternative["headline"],
                        "rationale": history.alternative["rationale"],
                        "sources": [_cite(s, registry, pages) for s in history.alternative["sources"]]},
        "claim_class": "cited_history",
        "meta": response_meta(request),
    }
