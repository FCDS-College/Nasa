"""L-4: the hand-authored contract (ADR-010) and the FastAPI routes describe the same API."""
import re

from fastapi.routing import APIRoute

from api_contract import CONTRACT_PATH
from flame_api.main import app

UNDOCUMENTED = {("GET", "/health/live"), ("GET", "/api/")}


def _contract_operations():
    import json

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return {(method.upper(), path) for path, item in contract["paths"].items() for method in item
            if method in {"get", "put", "post", "delete", "patch"}}, contract


def _api_routes(routes):
    """APIRoutes, including those of included routers (newer FastAPI wraps them in _IncludedRouter)."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif getattr(route, "original_router", None) is not None:
            yield from _api_routes(route.original_router.routes)


def _route_operations():
    operations = set()
    for route in _api_routes(app.routes):
        path = re.sub(r"\{(\w+):[^}]+\}", r"{\1}", route.path)
        operations |= {(method, path) for method in route.methods if method != "HEAD"}
    return operations


def test_every_route_is_in_the_contract_and_every_contract_operation_is_served():
    contract_ops, _ = _contract_operations()
    route_ops = _route_operations() - UNDOCUMENTED
    assert route_ops - contract_ops == set(), "routes missing from docs/api/openapi.json"
    assert contract_ops - route_ops == set(), "contract operations with no route"


def test_operations_that_reach_flames_model_path_or_change_config_are_excluded_from_aura():
    _, contract = _contract_operations()
    excluded = {(m.upper(), p) for p, item in contract["paths"].items() for m, op in item.items()
                if isinstance(op, dict) and op.get("x-aura-exclude") is True}
    assert {("POST", "/api/chat"), ("PUT", "/api/admin/ai/mode"), ("GET", "/api/ai/providers")} <= excluded
    writes_not_excluded = {(m.upper(), p) for p, item in contract["paths"].items() for m, op in item.items()
                           if m in {"post", "put", "patch", "delete"} and not op.get("x-aura-exclude")}
    # AURA only compiles GET operations into tools today; POST /api/analyses stays visible as a write
    # AURA cannot call. Any new write must be a deliberate choice.
    assert writes_not_excluded == {("POST", "/api/analyses")}


def test_every_operation_has_a_unique_operation_id_and_a_200_example():
    _, contract = _contract_operations()
    ids = [op["operationId"] for item in contract["paths"].values() for op in item.values() if isinstance(op, dict)]
    assert len(ids) == len(set(ids))
    for path, item in contract["paths"].items():
        get = item.get("get")
        if get is None or path.endswith("/artifacts/{artifact_kind}"):   # binary download, no JSON example
            continue
        media = get["responses"]["200"]["content"]["application/json"]
        assert media.get("examples"), f"GET {path} needs a 200 example (AURA's dry run validates tools against it)"
