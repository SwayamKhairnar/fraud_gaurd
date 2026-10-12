# Contracts

The single source of truth for what `fraud-detection-service` and `fraud-ml-service` send each other. Decision background: `docs/adr/0002-contract-first.md`.

**Current version: 1.0 (draft, to be frozen at the end of Phase 1).**

## Files

| File | Describes |
|---|---|
| `predict-request.schema.json` | Body of `POST /v1/predict` |
| `predict-response.schema.json` | Successful response body |
| `error.schema.json` | Body of every non-2xx response |
| `examples/request.transfer.json` | A valid TRANSFER request (scored by the model) |
| `examples/request.payment.json` | A valid PAYMENT request (not scored by the v1 model) |
| `examples/response.block.json` | A scored response recommending BLOCK |
| `examples/response.unscored.json` | Response for an unsupported type (`scored_by_model=false`) |
| `examples/error.validation.json` | A validation error |

## Request fields

| Field | Required | Type | Used by v1 model | Notes |
|---|---|---|---|---|
| `schema_version` | yes | `"1.0"` | no | Contract version |
| `txn_id` | yes | string (1..64) | no | Echoed back; idempotency key |
| `timestamp` | yes | RFC 3339 date-time | yes | Hour of day and day-of-week are derived from it |
| `type` | yes | enum | yes | `TRANSFER`, `CASH_OUT` are scored; `PAYMENT`, `CASH_IN`, `DEBIT` are not (v1) |
| `amount` | yes | number > 0 | yes | |
| `currency` | no | ISO 4217 | no | Default `INR` |
| `sender_account` | yes | string | no (identity only) | Used by the caller to build context; not a model input |
| `receiver_account` | yes | string | no (identity only) | Same |
| `channel` | no | enum | no | Reserved for later models |
| `sender_balance_before` | no | number >= 0 | **no (ignored)** | See ADR-0005 |
| `receiver_balance_before` | no | number >= 0 | **no (ignored)** | See ADR-0005 |
| `context` | yes | object | yes | History features, see below |
| `metadata` | no | object | no | Free-form extension point |

### `context` (all required, all computed by the caller)

| Field | Type | Meaning (summary; the exact formulas are in `fraud-ml-service/docs/02-feature-spec.md`) |
|---|---|---|
| `sender_txn_count_1h` | int >= 0 | Sender's earlier transactions in the current hour bucket |
| `sender_txn_count_24h` | int >= 0 | Same, over 24 hour buckets |
| `sender_amount_sum_24h` | number >= 0 | Sum of those amounts |
| `sender_unique_receivers_24h` | int >= 0 | Distinct receivers paid in 24h |
| `sender_avg_amount_30d` | number or null | Mean earlier amount over 30d; null if none |
| `is_new_receiver` | bool | Sender never paid this receiver in the 30d window |
| `receiver_incoming_count_24h` | int >= 0 | Earlier incoming transactions to the receiver in 24h |
| `receiver_unique_senders_24h` | int >= 0 | Distinct senders that paid the receiver in 24h |

All counts and sums **exclude the current transaction**.

## Response fields

| Field | Type | Notes |
|---|---|---|
| `schema_version` | `"1.0"` | |
| `txn_id` | string | Echo |
| `scored_by_model` | bool | False means "no model opinion; use your rules" |
| `fraud_score` | number 0..1 or null | null iff `scored_by_model` is false |
| `decision` | `ALLOW` / `REVIEW` / `BLOCK` | Recommendation. Always `ALLOW` when unscored |
| `reason_codes` | array of enum | Up to 5, most important first |
| `model_version` | string `vN` | Which model produced it |
| `latency_ms` | number | Server-side time |
| `scored_at` | date-time | UTC |

The decision is a **recommendation**. `fraud-detection-service` combines it with its own rules and makes the final call.

## Rules of the contract

1. **Strict:** unknown top-level fields are rejected (HTTP 422). Use `metadata` for experiments.
2. **Nulls:** only fields marked "or null" may be null. Everything else must be present and valid.
3. **Exclusion of current transaction:** the caller must not count the transaction being scored in `context`.
4. **Idempotent:** the same request returns the same score for the same model version.
5. **Time:** timestamps are UTC unless an offset is given.

## Validating a payload

From `fraud-ml-service` with the dev dependencies installed:

```bash
python - <<'PY'
import json, jsonschema
schema = json.load(open("../contracts/predict-request.schema.json"))
payload = json.load(open("../contracts/examples/request.transfer.json"))
jsonschema.Draft202012Validator(schema).validate(payload)
print("valid")
PY
```

The automated version of this runs in `fraud-ml-service/tests/contract/` and validates **every** file in `examples/` against its schema, and checks the Pydantic models against the schemas.

## Using the contract from Java (later)

- Hand-write DTOs matching the schemas, or generate them with a JSON-Schema-to-POJO tool.
- In the Java service's tests, validate outgoing requests against `predict-request.schema.json`.
- Treat the response `fraud_score` as nullable; always branch on `scored_by_model` first.

## Changing the contract

Follow the process in `docs/05-maintenance.md` section 3. In short: ADR, edit schemas and examples, bump `schema_version` (MINOR   for additive optional fields, MAJOR for breaking), update models and docs, run contract tests, update CHANGELOG, then roll out consumers before producers (unless purely additive).

## Planned changes (not in v1.0)

| Idea | Likely version |
|---|---|
| Merchant and geo fields for card payments (Sparkov backup path) | 1.1 (additive) |
| Batch endpoint (`/v1/predict/batch`) | 1.1 (new schema file) |
| Per-feature explanations (SHAP values) | 1.1 (additive response field) |
