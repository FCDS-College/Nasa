"""Contract assertions shared by the API tests.

A plain module, not conftest: with the repo-root `--import-mode=importlib`, a test cannot
`import conftest`, and the name would be ambiguous between the two test trees anyway.
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver

CONTRACT_PATH = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.json"


def assert_contract_component(instance, component_name):
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(
        contract["components"]["schemas"][component_name],
        resolver=RefResolver.from_schema(contract),
    )
    errors = list(validator.iter_errors(instance))
    assert not errors, "\n".join(f"{list(error.absolute_path)}: {error.message}" for error in errors)


