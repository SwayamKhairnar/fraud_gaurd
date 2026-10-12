# 09. Definition of Done: fraud-ml-service v0.1.0

The ML service counts as **finished for hand-off** when every box below is ticked. This is the checklist that closes Phase 6.

## A. Functional
- [ ] `POST /v1/predict` returns a valid response for TRANSFER and CASH_OUT
- [ ] Unsupported types return `scored_by_model=false`, `fraud_score=null`, `decision=ALLOW`
- [ ] Decision thresholds come from configuration and the model version, not hard-coded values
- [ ] Reason codes returned for REVIEW and BLOCK
- [ ] `/v1/model-info`, `/health/live`, `/health/ready`, `/metrics` implemented
- [ ] Startup refuses to become ready if the model or feature list is invalid

## B. Contract
- [ ] Contract v1.0 frozen and tagged (`contracts-v1.0`)
- [ ] All examples validate; contract tests pass
- [ ] Pydantic models match the JSON Schemas
- [ ] Error format matches `error.schema.json` for 401, 422, 503, 500

## C. Model
- [ ] Model trained on the time-based split; leakage checks passed
- [ ] Beats the trivial rule and the logistic-regression baseline on validation PR-AUC
- [ ] Final test metrics recorded once in `metrics.json`
- [ ] Artifacts exported to `artifacts/models/v1/` with `CURRENT` set
- [ ] Model card completed, including honest limitations

## D. Quality
- [ ] Unit, contract, API, model, and parity tests pass
- [ ] Coverage on `app/` at least 80%
- [ ] `ruff check .` clean
- [ ] Parity test shows zero feature mismatches on the replay sample

## E. Operability
- [ ] Dockerfile builds; container becomes ready and answers requests
- [ ] `docker compose up` works from a clean clone with the model volume mounted
- [ ] Prometheus scrapes the service; dashboard shows rate, latency, errors, decisions, score distribution
- [ ] Structured JSON logs with request ID; no raw account IDs logged
- [ ] Load test run; p95 and p99 recorded and within targets (or deviations explained)
- [ ] Runbook steps for start, promote, and rollback verified at least once

## F. Documentation and hand-off
- [ ] `README.md` quick start works on a clean machine
- [ ] Integration guide verified against the running service
- [ ] `scripts/mock_client.py` produces realistic traffic for downstream development
- [ ] CHANGELOG updated (Contract and Model sections)
- [ ] Tag `fraud-ml-service-v0.1.0` created
- [ ] Known gaps recorded as roadmap items (not left implicit)

## G. Explicit non-requirements for v0.1.0
Batch endpoint, retraining pipeline, drift job, SHAP explanations, authentication beyond the optional API key, Kubernetes manifests, distributed tracing.
