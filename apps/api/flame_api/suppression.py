"""Suppression Advisor endpoint (plan docs/plan/SUPPRESSION_ADVISOR_PLAN.md).

    GET /api/insights/suppression-advice    CO₂ vs water-mist PFE recommendation for a cabin

The decision is made by ``ai.fire_safety.suppression.advisor`` (deterministic, no language model).
This layer adds the FLEX outcome model with its nearest real flight tests, from the ingested rows.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ai.fire_safety.suppression import advisor
from ai.fire_safety.suppression import constants as C
from flame_api import investigations
from flame_api.contracts import response_meta
from flame_api.database import get_session

router = APIRouter()


@router.get("/api/insights/suppression-advice", tags=["Fire safety"])
def suppression_advice(
    request: Request,
    fire_type: Literal["heptane", "methanol", "other_liquid", "electrical_battery", "solid"] = "heptane",
    cabin_volume_m3: Annotated[float, Query(ge=1.0, le=2000.0)] = C.DEFAULT_CABIN_VOLUME_M3,
    pressure_kpa: Annotated[float, Query(ge=5.0, le=400.0)] = 101.3,
    o2_fraction: Annotated[float, Query(gt=0.0, lt=1.0)] = 0.21,
    co2_fraction: Annotated[float, Query(ge=0.0, le=0.9)] = 0.0,
    temperature_k: Annotated[float, Query(ge=250.0, le=350.0)] = C.DEFAULT_CABIN_TEMPERATURE_K,
    zone: Literal["well_mixed", "local"] = "well_mixed",
    local_zone_fraction: Annotated[float, Query(gt=0.0, le=1.0)] = C.DEFAULT_LOCAL_ZONE_FRACTION,
    delivery_fraction: Annotated[float, Query(ge=0.0, le=1.0)] = C.DEFAULT_DELIVERY_FRACTION,
    droplet_diameter_mm: Annotated[float, Query(gt=0.0, le=20.0)] = 3.0,
    session: Session = Depends(get_session),
):
    if o2_fraction + co2_fraction > 1.0 + 1e-9:
        return investigations._bad(request, "o2_fraction", "o2_fraction + co2_fraction cannot exceed 1")
    inp = advisor.AdviceInput(fire_type=fire_type, cabin_volume_m3=cabin_volume_m3, pressure_kpa=pressure_kpa,
                              o2_fraction=o2_fraction, co2_fraction=co2_fraction, temperature_k=temperature_k, zone=zone,
                              local_zone_fraction=local_zone_fraction, delivery_fraction=delivery_fraction,
                              droplet_diameter_mm=droplet_diameter_mm)
    flex_predict = None
    if fire_type in advisor.FLEX_FUEL:
        _, by_source, _, _, _ = investigations._load(session)
        tests = by_source.get("FF-PSI-69", [])
        if tests:
            def flex_predict(features: dict) -> dict:
                return investigations.predict(features, tests, k=5)
    return {**advisor.advise(inp, flex_predict), "meta": response_meta(request)}
