"""Contract tests: schemas are valid, examples validate, and known-bad payloads are rejected."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"


def _load(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(_load(schema_name), format_checker=FormatChecker())


REQUEST = "predict-request.schema.json"
RESPONSE = "predict-response.schema.json"
ERROR = "error.schema.json"


@pytest.mark.contract
@pytest.mark.parametrize("schema_name", [REQUEST, RESPONSE, ERROR])
def test_schema_is_valid_json_schema(schema_name):
    Draft202012Validator.check_schema(_load(schema_name))


@pytest.mark.contract
@pytest.mark.parametrize(
    ("example", "schema_name"),
    [
        ("examples/request.transfer.json", REQUEST),
        ("examples/request.payment.json", REQUEST),
        ("examples/response.block.json", RESPONSE),
        ("examples/response.unscored.json", RESPONSE),
        ("examples/error.validation.json", ERROR),
    ],
)
def test_example_matches_schema(example, schema_name):
    _validator(schema_name).validate(_load(example))


@pytest.mark.contract
def test_every_example_file_is_covered_by_a_prefix_rule():
    prefixes = {"request", "response", "error"}
    for path in (CONTRACTS / "examples").glob("*.json"):
        assert path.name.split(".", 1)[0] in prefixes, f"unmatched example: {path.name}"


# ---- known-bad requests must be rejected --------------------------------------------------------


def _bad_request_cases():
    base = _load("examples/request.transfer.json")

    def mutate(fn):
        payload = copy.deepcopy(base)
        fn(payload)
        return payload

    return {
        "negative_amount": mutate(lambda p: p.update(amount=-5)),
        "zero_amount": mutate(lambda p: p.update(amount=0)),
        "unknown_top_level_field": mutate(lambda p: p.update(surprise=1)),
        "bad_type": mutate(lambda p: p.update(type="WIRE")),
        "bad_schema_version": mutate(lambda p: p.update(schema_version="2.0")),
        "missing_context": mutate(lambda p: p.pop("context")),
        "missing_context_field": mutate(lambda p: p["context"].pop("is_new_receiver")),
        "negative_count": mutate(lambda p: p["context"].update(sender_txn_count_1h=-1)),
        "float_count": mutate(lambda p: p["context"].update(sender_txn_count_1h=1.5)),
        "unknown_context_field": mutate(lambda p: p["context"].update(extra=1)),
        "bad_currency": mutate(lambda p: p.update(currency="inr")),
        "bad_account_chars": mutate(lambda p: p.update(sender_account="bad account!")),
        "null_in_non_nullable": mutate(lambda p: p["context"].update(sender_txn_count_24h=None)),
    }


@pytest.mark.contract
@pytest.mark.parametrize("case", sorted(_bad_request_cases()))
def test_bad_request_is_rejected(case):
    payload = _bad_request_cases()[case]
    assert list(_validator(REQUEST).iter_errors(payload)), f"{case} should have been rejected"


@pytest.mark.contract
def test_nullable_average_is_accepted():
    payload = _load("examples/request.transfer.json")
    payload["context"]["sender_avg_amount_30d"] = None
    _validator(REQUEST).validate(payload)


# ---- response rules -------------------------------------------------------------------------------


@pytest.mark.contract
def test_unscored_response_must_have_null_score_and_allow():
    response = _load("examples/response.unscored.json")
    validator = _validator(RESPONSE)

    wrong_score = copy.deepcopy(response)
    wrong_score["fraud_score"] = 0.5
    assert list(validator.iter_errors(wrong_score))

    wrong_decision = copy.deepcopy(response)
    wrong_decision["decision"] = "BLOCK"
    assert list(validator.iter_errors(wrong_decision))


@pytest.mark.contract
def test_scored_response_must_have_numeric_score():
    response = _load("examples/response.block.json")
    response["fraud_score"] = None
    assert list(_validator(RESPONSE).iter_errors(response))


@pytest.mark.contract
def test_score_out_of_range_is_rejected():
    response = _load("examples/response.block.json")
    for bad in (-0.1, 1.1):
        response["fraud_score"] = bad
        assert list(_validator(RESPONSE).iter_errors(response))


@pytest.mark.contract
def test_model_version_pattern():
    response = _load("examples/response.block.json")
    response["model_version"] = "v2-card"
    assert list(_validator(RESPONSE).iter_errors(response))
