# 06. Testing Strategy

Tests exist to protect three things: the **contract**, the **feature definitions**, and the **model's behaviour**. Layout under `tests/`.

## 1. Test layers

| Layer | Folder | What it proves | Speed |
|---|---|---|---|
| Unit | `tests/unit/` | Feature functions, threshold logic, reason codes, config loading | fast |
| Contract | `tests/contract/` | Examples match schemas; Pydantic models match schemas | fast |
| API | `tests/api/` | Endpoints, status codes, error format, headers, metrics endpoint | fast |
| Model | `tests/model/` | Artifact loads; feature list matches; deterministic; smoke predictions; regression gate | medium |
| Parity | `tests/parity/` | Streaming reference features equal offline training features | medium |
| Container | script / CI | Image builds, starts, becomes ready, answers a request | slow |
| Performance | `scripts/` | Latency under load meets targets | slow |

Mark slow tests with `@pytest.mark.slow` so `pytest -m "not slow"` stays quick.

## 2. Unit tests: feature functions (most important)

Use tiny hand-built transaction logs (5 to 15 rows) and assert exact outputs. Required cases:

- First-ever transaction for a sender (counts 0, `sender_avg_amount_30d` null, `is_new_receiver` true)
- Two transactions in the same hour bucket (the second sees the first, the first does not see the second)
- A transaction exactly 24 buckets earlier is **excluded** from the 24h window; 23 buckets earlier is **included**
- 719 versus 720 buckets for the 30d window
- Same receiver paid twice (not new the second time; not new within 30d, new again after 30d)
- Other transaction types count toward history
- Receiver fan-in: distinct senders versus total incoming
- Ties: identical `step` resolved by original row order
- Amount ratios when the average is null or zero

## 3. Contract tests

1. Every file in `contracts/examples/` validates against its schema (request examples against the request schema, response examples against the response schema, error examples against the error schema).
2. The Pydantic request/response models accept every valid example and reject known-bad variants: negative amount, missing context field, unknown top-level field, bad `type`, bad `schema_version`.
3. The JSON Schema generated from the Pydantic models is compared to the files in `contracts/` for field names, required lists, and enum values. Any drift fails the test.
4. The unscored response (`scored_by_model=false`) must have `fraud_score=null` and `decision=ALLOW`; the scored response must have a numeric score.

## 4. API tests (FastAPI `TestClient`)

- 200 for a valid TRANSFER; body validates against the response schema
- 200 `scored_by_model=false` for PAYMENT
- 422 with `VALIDATION_ERROR` and per-field `details` for a bad body; body validates against the error schema
- 503 `MODEL_NOT_READY` when the model is not loaded
- 401 when the API key is enabled and missing
- `X-Request-ID` echoed or generated; `X-Model-Version` present
- `/health/live` is 200 even without a model; `/health/ready` is 503 without a model
- `/metrics` exposes the documented metric names after one request
- Idempotency: the same request twice gives identical score and decision

## 5. Model tests

- The artifact in `artifacts/models/<CURRENT>/` loads and its `feature_list.json` equals the code's feature list
- Predictions are deterministic for the same input
- Three canned inputs behave sensibly: an obviously ordinary transfer scores low; a high-amount, new-receiver, high-fan-in transfer scores clearly higher than the ordinary one
- **Regression gate:** a small stored evaluation sample (`tests/fixtures/eval_sample.parquet`, a few thousand rows including some fraud) must reach at least the PR-AUC recorded in `metrics.json` minus a tolerance. Prevents silent breakage when libraries or code change
- Score is always within 0 and 1; no NaN

These tests are skipped with a clear message if no model artifact exists yet.

## 6. Parity tests

Replay at least 50,000 rows through the streaming reference implementation in event order and compare each context feature to the offline table. Zero mismatches allowed (exact for ints and booleans, tolerance 1e-6 for floats). Details: `02-feature-spec.md`, section 7.

## 7. Container test

```bash
docker build -t fraud-ml-service:test .
docker run -d --name fraud-ml-test -p 8000:8000 \
  -v "$(pwd)/artifacts/models:/srv/artifacts/models:ro" fraud-ml-service:test
# wait for readiness
curl --retry 20 --retry-delay 1 --retry-connrefused -f http://localhost:8000/health/ready
curl -f -X POST http://localhost:8000/v1/predict -H "Content-Type: application/json" \
  -d @../contracts/examples/request.transfer.json
docker rm -f fraud-ml-test
```

## 8. Performance test

`scripts/load_test.py` (to be written; a simple async client or Locust):
- Warm up with 200 requests, then 10,000 requests at a fixed concurrency (for example 8)
- Record p50 / p95 / p99 latency and throughput, and the machine used
- Compare against the targets in `docs/01-architecture.md`
- Record results in the model card

## 9. Coverage and quality gates

- Target: at least 80% line coverage on `app/` (`pytest --cov=app`)
- `ruff check .` clean
- Optional: `mypy app` clean on public functions

## 10. Continuous integration (when the repo is on GitHub)

A workflow that, on every push and pull request, installs dependencies, runs `ruff check .`, runs `pytest -m "not slow"`, and builds the Docker image. Parity and model tests run on demand or nightly because they need data or artifacts.

## 11. Test data policy

- Fixtures are small and committed (`tests/fixtures/`); they are synthetic or a tiny PaySim-derived sample.
- Never commit the full dataset.
- Any bug found in production-like use gets a regression test first.
