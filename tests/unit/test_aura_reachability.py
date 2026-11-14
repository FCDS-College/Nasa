"""Which optional query parameters AURA can reach (tests/integration/aura_blueprint_dryrun.py), checked without AURA.

AURA carries at most AURA_MAX_OPTIONAL_QUERY optional query parameters per generated tool, in spec order
(aura_core/adaptation/normalize.py, MAX_OPTIONAL_QUERY at the pinned revision). A parameter past the cap is unreachable by
design; the contract says so with `x-aura-unreachable` (the reason), and the dry run fails on any other unreachable one.
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("aura_blueprint_dryrun", ROOT / "tests" / "integration" / "aura_blueprint_dryrun.py")
dryrun = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dryrun)
CONTRACT = json.loads((ROOT / "docs" / "api" / "openapi.json").read_text(encoding="utf-8"))


def _spec_with(params):
    return {"paths": {"/a": {"get": {"parameters": params}}, "/b": {"get": {"parameters": [
        {"name": "shared", "in": "query", "required": False, "schema": {"type": "number"}}]}}}}


def _q(name, **extra):
    return {"name": name, "in": "query", "required": False, "schema": {"type": "number"}, **extra}


def test_reachability_is_judged_per_endpoint_not_across_all_tools():
    """`shared` reaches AURA on /b but not on /a; the old check, a union over all tools, missed that."""
    spec = _spec_with([_q("x"), _q("shared")])
    result = dryrun.reachability(spec, {"/a": {"x"}, "/b": {"shared"}})
    assert result["unexpected"] == [("/a", "shared")]


def test_a_documented_unreachable_parameter_is_reported_but_allowed():
    spec = _spec_with([_q("x"), _q("y", **{"x-aura-unreachable": "past AURA's cap"})])
    result = dryrun.reachability(spec, {"/a": {"x"}, "/b": {"shared"}})
    assert result["unexpected"] == [] and result["documented"] == [("/a", "y", "past AURA's cap")]


def test_a_documented_parameter_that_aura_does_reach_is_a_stale_note():
    spec = _spec_with([_q("x"), _q("y", **{"x-aura-unreachable": "past AURA's cap"})])
    result = dryrun.reachability(spec, {"/a": {"x", "y"}, "/b": {"shared"}})
    assert result["stale"] == [("/a", "y")]


def test_excluded_operations_and_required_or_header_parameters_are_ignored():
    spec = {"paths": {"/a": {"get": {"x-aura-exclude": True, "parameters": [_q("z")]}},
                      "/b": {"get": {"parameters": [{"name": "X-Request-ID", "in": "header"},
                                                    {"name": "id", "in": "query", "required": True}]}}}}
    assert dryrun.reachability(spec, {})["unexpected"] == []


def test_only_parameters_past_auras_cap_are_marked_unreachable_in_the_contract():
    """A mark on a parameter inside the first AURA_MAX_OPTIONAL_QUERY would hide a real gap; every mark carries a reason."""
    for path, item in CONTRACT["paths"].items():
        operation = item.get("get")
        if not operation or operation.get("x-aura-exclude"):
            continue
        optional = dryrun.optional_query_parameters(CONTRACT, operation)
        for position, param in enumerate(optional, start=1):
            note = param.get("x-aura-unreachable")
            if position <= dryrun.AURA_MAX_OPTIONAL_QUERY:
                assert note is None, f"{path} {param['name']} is within AURA's cap but marked unreachable"
            else:
                assert isinstance(note, str) and note.strip(), f"{path} {param['name']} is past AURA's cap and unmarked"


def test_the_suppression_advice_endpoint_documents_its_two_parameters_past_the_cap():
    operation = CONTRACT["paths"]["/api/insights/suppression-advice"]["get"]
    past_cap = [p["name"] for p in dryrun.optional_query_parameters(CONTRACT, operation)[dryrun.AURA_MAX_OPTIONAL_QUERY:]]
    assert past_cap == ["delivery_fraction", "droplet_diameter_mm"]
