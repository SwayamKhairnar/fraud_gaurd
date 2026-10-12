"""Validate every contract example against its schema.

Run from the fraud-ml-service/ directory:
    python -m scripts.check_contracts

Exit code 0 = everything valid; 1 = at least one problem.
Rule: examples are matched to schemas by file-name prefix (request.* / response.* / error.*).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"

SCHEMA_FOR_PREFIX = {
    "request": "predict-request.schema.json",
    "response": "predict-response.schema.json",
    "error": "error.schema.json",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def check_schemas() -> list[str]:
    """Each schema file must itself be a valid JSON Schema."""
    problems = []
    for schema_name in SCHEMA_FOR_PREFIX.values():
        schema = load_json(CONTRACTS_DIR / schema_name)
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # noqa: BLE001 - report any schema problem
            problems.append(f"{schema_name}: invalid schema: {exc}")
    return problems


def check_examples() -> list[str]:
    """Each example must validate against the schema chosen by its file-name prefix."""
    problems = []
    for example in sorted((CONTRACTS_DIR / "examples").glob("*.json")):
        prefix = example.name.split(".", 1)[0]
        schema_name = SCHEMA_FOR_PREFIX.get(prefix)
        if schema_name is None:
            problems.append(f"{example.name}: no schema for prefix '{prefix}'")
            continue
        validator = Draft202012Validator(
            load_json(CONTRACTS_DIR / schema_name), format_checker=FormatChecker()
        )
        errors = sorted(validator.iter_errors(load_json(example)), key=lambda e: list(e.path))
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            problems.append(f"{example.name}: {location}: {error.message}")
    return problems


def main() -> int:
    problems = check_schemas() + check_examples()
    if problems:
        print("Contract problems found:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    count = len(list((CONTRACTS_DIR / "examples").glob("*.json")))
    print(f"OK: {len(SCHEMA_FOR_PREFIX)} schemas valid, {count} examples valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
