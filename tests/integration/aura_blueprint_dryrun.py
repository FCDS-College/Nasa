"""Offline dry run: what AURA's Track AP pipeline would generate from Flame's API contract.

Runs AURA's own code -- AP3 OpenAPI discovery -> AP4 project twin -> AP5 capability plan ->
AP6 blueprint compiler -- over ``docs/api/openapi.json`` and then checks every compiled read tool's
output schema against the contract's own 200-response example, the same check AURA's tool
registry applies to live results (ADR-025). No network, no AURA server, no state.

Acceptance check for AURA requirement AR-1 in docs/integration/AURA_INTEGRATION_REQUIREMENTS.md:
exit code 0 only when every contract example would be accepted.

    AURA_BACKEND="E:/AURA AI/aura_backend" python tests/integration/aura_blueprint_dryrun.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

FLAME_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = FLAME_ROOT / "docs" / "api" / "openapi.json"


def main() -> int:
    backend = os.environ.get("AURA_BACKEND")
    if not backend or not Path(backend, "aura_core").is_dir():
        print("set AURA_BACKEND to an AURA checkout's aura_backend/ directory", file=sys.stderr)
        return 2
    sys.path.insert(0, backend)

    from aura_core.adaptation.compiler import compile_blueprint
    from aura_core.adaptation.planner import CapabilityRegistry, plan_capabilities
    from aura_core.adaptation.twin import build_twin
    from aura_core.adapters.connectors.openapi import artifacts_from_openapi, parse_spec
    from aura_core.domain.blueprint import ConnectorRef
    from aura_core.domain.connectors import ConnectorKind, IdentityMode
    from aura_core.domain.discovery import DiscoveryBudget
    from aura_core.domain.output_schema import output_errors

    spec = parse_spec(SPEC_PATH.read_bytes())
    report = artifacts_from_openapi("flame-api", spec, DiscoveryBudget())
    twin = build_twin("flame", 1, [report]).twin
    plan = plan_capabilities(twin, CapabilityRegistry.from_directory())
    ref = ConnectorRef("flame-api", ConnectorKind.OPENAPI, IdentityMode.SERVICE_ACCOUNT)
    compiled = compile_blueprint(twin, plan, connectors=[ref], version=1, name="Flame in Freefall")
    templates = {t.id: t for t in compiled.blueprint.templates}

    print(f"discovery: {len(report.artifacts)} artifacts, issues={len(report.issues)}")
    print(f"compiled tools: {len(compiled.blueprint.tools)}")
    rejected = 0
    missing_examples = 0
    for tool in compiled.blueprint.tools:
        http = templates[tool.template].http
        params = [p.name for p in tool.parameters]
        operation = spec["paths"].get(http.path, {}).get("get", {})
        content = operation.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {})
        example = content.get("example")
        if example is None and content.get("examples"):
            example = next(iter(content["examples"].values())).get("value")
        if example is None:
            verdict = "no example in contract"
            missing_examples += 1
        else:
            errors = output_errors(dict(tool.output_schema), example)
            verdict = "ACCEPTED" if not errors else "REJECTED: " + "; ".join(errors)
            rejected += bool(errors)
        print(f"  {tool.name:28} GET {http.path:45} params={params}  {verdict}")

    # ADR-004: operations Flame marks x-aura-exclude (chat, AI status, admin writes) must never be tools.
    excluded = {(m.upper(), p) for p, item in spec["paths"].items() for m, op in item.items()
                if isinstance(op, dict) and op.get("x-aura-exclude") is True}
    leaked = 0
    for tool in compiled.blueprint.tools:
        http = templates[tool.template].http
        if ("GET", http.path) in excluded or any(path == http.path for _, path in excluded):
            print(f"  LEAKED: excluded operation compiled into tool {tool.name} ({http.path})")
            leaked += 1
    excluded_issues = sum(1 for issue in report.issues if issue.code == "operation_excluded")
    print(f"excluded by x-aura-exclude: {len(excluded)} operations, {excluded_issues} reported by discovery")
    if excluded_issues != len(excluded):
        print("  AURA revision does not honor x-aura-exclude (needs AURA PR #166 or later)")
        leaked += 1

    exposed = {p for tool in compiled.blueprint.tools for p in templates[tool.template].http.query_params}
    unreachable = 0
    for path, item in sorted(spec["paths"].items()):
        if ("GET", path) in excluded:
            continue
        for param in item.get("get", {}).get("parameters", []):
            param = _resolve(spec, param)
            if param.get("in") == "query" and param.get("name") not in exposed:
                print(f"  not reachable by AURA: optional query parameter {param.get('name')!r} on GET {path}")
                unreachable += 1
    return 1 if rejected or missing_examples or unreachable or leaked else 0


def _resolve(spec: dict, node: dict) -> dict:
    ref = node.get("$ref")
    if not ref:
        return node
    target = spec
    for part in ref.lstrip("#/").split("/"):
        target = target[part]
    return target


if __name__ == "__main__":
    sys.exit(main())
