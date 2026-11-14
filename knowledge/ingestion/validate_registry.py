"""Validate datasets/registry/source_registry.csv against source_registry.schema.json (M9, E2-1).

    python knowledge/ingestion/validate_registry.py            # exit 0 = valid
    python knowledge/ingestion/validate_registry.py --json     # decoded rows, for inspection

Runs in CI (.github/workflows/ci.yml, job `registry`). Uses the same decoder as the API seed, so a
row that validates here is loaded exactly as validated. A source with files in files.jsonl must also be
cleared: verified and licensed (KB audit 2026-11-13); flame_api.registry.KNOWN_UNCLEARED lists the exceptions.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from flame_api.registry import REGISTRY_CSV, clearance_warnings, read_registry, validate_registry  # noqa: E402


def main(argv: list[str]) -> int:
    path = Path(argv[argv.index("--csv") + 1]) if "--csv" in argv else REGISTRY_CSV
    if "--json" in argv:
        print(json.dumps(read_registry(path), indent=2))
        return 0
    problems = validate_registry(path)
    rows = read_registry(path)
    for problem in problems:
        print(f"INVALID {problem}")
    for warning in clearance_warnings(path):
        print(f"NOT CLEARED (allowed: not ingested) {warning}")
    print(f"{len(rows)} sources checked, {len(problems)} problems ({path.relative_to(ROOT) if path.is_relative_to(ROOT) else path})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
