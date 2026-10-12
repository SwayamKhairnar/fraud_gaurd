# fraud-ml-service

The machine-learning scoring microservice of the digital banking fraud system. It takes one transaction (plus its history features) and returns a fraud risk score, a recommended decision (ALLOW / REVIEW / BLOCK), reason codes, and the model version that produced them.

It is **stateless** and **contract-driven**: it knows nothing about accounts, databases, Redis, or Kafka. See `../docs/adr/0004-stateless-ml-service.md`.

## Status

Phase 0 complete (scaffold, docs, contracts, configuration). Code is created during Phases 2 to 5 (see `../docs/02-roadmap.md`). Files marked *(to create)* below do not exist yet.

## Quick start

```bash
cd fraud-ml-service
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt -r requirements-train.txt
cp .env.example .env
```

Full environment setup (Python, Docker, Kaggle): `../docs/03-dev-environment.md`.

Once the service code exists:

```bash
uvicorn app.main:app --port 8000        # or: make serve
curl -X POST localhost:8000/v1/predict -H "Content-Type: application/json" \
     -d @../contracts/examples/request.transfer.json
```

`make` is optional. Every target in the `Makefile` is a short command you can run by hand.

## Folder structure

```
fraud-ml-service/
├── app/                       <- the running service
│   ├── main.py                <- FastAPI app, startup (loads the model)          (to create)
│   ├── api/                   <- HTTP layer only: routers for predict, health, model-info, metrics
│   ├── core/                  <- config, logging, metrics, error handling
│   ├── features/              <- feature code SHARED by training and serving (pure functions)
│   │   ├── per_request.py     <- amount_log, ratios, hour of day...             (to create)
│   │   └── context.py         <- streaming reference implementation of context  (to create)
│   ├── model/                 <- model loader, predictor, thresholds, reason codes
│   └── schemas/               <- Pydantic request/response/error models (mirror ../contracts)
├── training/                  <- offline pipeline: data prep, features, train, evaluate, export
├── scripts/                   <- mock client, replay stream, load test, helpers
├── tests/
│   ├── unit/                  <- feature functions, thresholds, reason codes
│   ├── contract/              <- examples vs schemas, Pydantic vs schemas
│   ├── api/                   <- endpoint tests
│   ├── model/                 <- artifact + regression tests                    (to create)
│   ├── parity/                <- streaming vs offline feature equality          (to create)
│   └── fixtures/              <- small committed test data                      (to create)
├── notebooks/                 <- EDA and experiments (not production code)
├── config/                    <- settings.yaml, thresholds.yaml, training.yaml
├── docs/                      <- ML-service documentation (index below)
├── data/                      <- raw/ and processed/ (git-ignored)
├── artifacts/models/          <- versioned models: vN/ directories plus CURRENT pointer
├── Dockerfile  .dockerignore  Makefile  pyproject.toml
├── requirements.txt           <- runtime dependencies
├── requirements-dev.txt       <- test, lint
├── requirements-train.txt     <- notebooks, Kaggle CLI, plotting
└── .env.example
```

Layering rule: `api` calls `model` and `features`; `model` and `features` never import from `api`. Features are pure functions with no I/O.

## Documentation index

| Doc | Read it to learn |
|---|---|
| `docs/01-dataset-plan.md` | Which data, why, the time split, and the backup plan |
| `docs/02-feature-spec.md` | The exact definition of every feature (most important) |
| `docs/03-training-plan.md` | Step-by-step training, evaluation, thresholds, export |
| `docs/04-api-spec.md` | Endpoints, status codes, behaviour |
| `docs/05-observability.md` | Metrics, logs, dashboard, alerts, drift |
| `docs/06-testing-strategy.md` | What is tested and how |
| `docs/07-runbook.md` | Start/stop, troubleshooting, promote/rollback a model |
| `docs/08-model-card-template.md` | Per-model documentation template |
| `docs/09-definition-of-done.md` | The checklist that closes the ML phase |
| `docs/10-integration-guide.md` | How other services should call this one |

Project-wide docs are in `../docs/`; the shared contract is in `../contracts/`.

## What this service does and does not do

| Does | Does not |
|---|---|
| Validate the request against the contract | Store or read history (no Redis, no DB) |
| Build features and score with the active model | Move money or make the final decision |
| Return score, decision, reason codes, model version | Call other services |
| Expose health, model info, Prometheus metrics | Train models at request time |

## Endpoints (summary)

`POST /v1/predict` · `GET /v1/model-info` · `GET /health/live` · `GET /health/ready` · `GET /metrics`. Details in `docs/04-api-spec.md`.

## Common commands

| Task | Command |
|---|---|
| Lint | `ruff check .` |
| Format | `ruff format .` |
| Fast tests | `pytest -m "not slow"` |
| All tests with coverage | `pytest --cov=app` |
| Download data | `kaggle datasets download -d ealaxi/paysim1 -p data/raw --unzip` |
| Run the service | `uvicorn app.main:app --port 8000` |
| Build the image | `docker build -t fraud-ml-service:dev .` |
| Run with compose | `cd ../infra && docker compose up --build` |
