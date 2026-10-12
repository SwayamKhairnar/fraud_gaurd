# 02. Roadmap

One **session** is about one focused working day. At about 2 sessions per week the ML phase (Phases 0 to 6) is roughly 3 weeks, which is **about half of the total project time**. That is why every phase below is time-boxed.

## Time-box rules

- If a phase passes 1.5x its budget, **cut scope** instead of extending. The cut list for each phase is given.
- Do not tune hyperparameters beyond one small, time-limited search.
- A "good enough" model behind a stable contract beats a better model with no service.

---

## Phase 0: Setup (0.5 session)

- [ ] Create the Git repository and push this scaffold
- [ ] Python virtual environment created, dependencies installed (`docs/03-dev-environment.md`)
- [ ] `pytest` and `ruff` run cleanly (even with zero tests)
- [ ] Docker installed and `docker run hello-world` works
- [ ] Kaggle API configured; PaySim downloaded to `fraud-ml-service/data/raw/`

**Exit criteria:** you can run the toolchain commands without errors.

## Phase 1: Contracts and data understanding (1 session)

- [ ] Re-read `contracts/` and `fraud-ml-service/docs/02-feature-spec.md`; fix anything unclear
- [ ] EDA notebook: class balance, fraud by type, amount distributions, fraud over time
- [ ] Confirm time-split boundaries; check fraud counts per split
- [ ] Go / no-go on PaySim using the backup triggers in `fraud-ml-service/docs/01-dataset-plan.md`
- [ ] Freeze contract v1.0 (tag `contracts-v1.0`)

**Cut list:** extra plots, secondary datasets.

## Phase 2: Feature pipeline (1 session)

- [ ] Implement the context features exactly as specified (hour buckets, point-in-time correct)
- [ ] Unit tests for each feature using small hand-made examples
- [ ] Build the processed training table; save to `data/processed/`
- [ ] Sanity checks pass (no future leakage, no nulls where not allowed)

**Cut list:** the two receiver features (`receiver_*`) if they cause schedule pressure. Update the contract before freezing.

## Phase 3: Model training and evaluation (1 session)

- [ ] Baseline (logistic regression) trained and evaluated
- [ ] LightGBM trained and evaluated on the same split
- [ ] Metrics: PR-AUC, recall at fixed precision, confusion matrices at candidate thresholds
- [ ] Thresholds chosen on the validation set; final numbers on the test set
- [ ] Artifacts exported to `artifacts/models/v1/` and `CURRENT` set
- [ ] Model card filled in

**Cut list:** hyperparameter search, calibration, SHAP.

## Phase 4: FastAPI service (1 session)

- [ ] Pydantic models match the JSON Schemas (contract test passes)
- [ ] `/v1/predict`, `/health/live`, `/health/ready`, `/v1/model-info`, `/metrics`
- [ ] Reason codes implemented (rule-based mapping from features)
- [ ] API tests and unit tests passing

**Cut list:** batch endpoint, API-key auth.

## Phase 5: Container and observability (1 session)

- [ ] Dockerfile builds; container passes health checks
- [ ] `docker compose up` brings the service up with the model mounted
- [ ] Prometheus scrapes `/metrics`; a basic Grafana dashboard exists
- [ ] `scripts/mock_client.py` sends realistic traffic; dashboard shows it
- [ ] Simple load test; latency numbers recorded in the model card

**Cut list:** Grafana polish (keep Prometheus), load-test tooling beyond a script.

## Phase 6: Hand-off (0.5 session)

- [ ] `docs/10-integration-guide.md` verified against the running service
- [ ] Definition of Done checklist complete (`fraud-ml-service/docs/09-definition-of-done.md`)
- [ ] Tag `fraud-ml-service-v0.1.0`
- [ ] CHANGELOG updated

**Exit criteria:** the other services can be built against the contract and the mock client with no further ML work.

---

## Later phases (outline only, to be planned in detail later)

| Phase | Service / topic | System design concepts it can demonstrate |
|---|---|---|
| 7 | `account-service` | Optimistic locking, idempotent operations |
| 8 | `transaction-service` | SAGA, outbox pattern, idempotency keys |
| 9 | `fraud-detection-service` | Redis hour-bucket counters, rules engine, circuit breaker + fallback, shadow mode |
| 10 | `notification-service` | Async consumers, retries, dead-letter queue |
| 11 | Observability across services | Distributed tracing, correlation IDs, SLO dashboards |
| 12 (stretch) | Feedback loop, retraining job, or AML/graph service | Data pipelines, model lifecycle |
