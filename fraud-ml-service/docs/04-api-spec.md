# 04. API Specification

Base path: `/v1` for business endpoints; operational endpoints are unversioned. Request/response bodies are defined by `contracts/`. FastAPI also generates interactive docs at `/docs` and the OpenAPI document at `/openapi.json`.

## 1. Endpoints

| Method | Path | Purpose | Auth |
|---|---|---|---|
| POST | `/v1/predict` | Score one transaction | optional API key |
| GET | `/v1/model-info` | Active model version, features, thresholds, training metrics summary | optional API key |
| GET | `/health/live` | Liveness: the process is up | none |
| GET | `/health/ready` | Readiness: model loaded and valid | none |
| GET | `/metrics` | Prometheus metrics | none (network-restricted in real deployments) |

Not in v1: batch scoring, model reload endpoint (reload = restart), admin endpoints.

## 2. `POST /v1/predict`

### Request
- Header `Content-Type: application/json`
- Optional header `X-Request-ID` (generated if absent and echoed in the response header)
- Optional header `X-API-Key` when `API_KEY_ENABLED=true`
- Body: `contracts/predict-request.schema.json`

### Behaviour
1. Validate the body against the contract. Failures return 422 with `VALIDATION_ERROR`.
2. If the model is not loaded, return 503 `MODEL_NOT_READY`.
3. If `type` is not TRANSFER or CASH_OUT: return `scored_by_model=false`, `fraud_score=null`, `decision=ALLOW`, `reason_codes=["UNSCORED_TYPE"]`. No model call.
4. Otherwise build the features, score, apply thresholds, compute reason codes, and respond.
5. Record metrics and a structured log line.

Decision rule:

```
score >= block_threshold   -> BLOCK
score >= review_threshold  -> REVIEW
otherwise                  -> ALLOW
```

### Responses

| Status | Body | When |
|---|---|---|
| 200 | `predict-response.schema.json` | Success (scored or unscored) |
| 401 | `error.schema.json` (`UNAUTHORIZED`) | API key required and missing or wrong |
| 422 | `error.schema.json` (`VALIDATION_ERROR` or `UNSUPPORTED_SCHEMA_VERSION`) | Body does not match the contract |
| 503 | `error.schema.json` (`MODEL_NOT_READY`) | Model not loaded |
| 500 | `error.schema.json` (`INTERNAL_ERROR`) | Unexpected failure |

Response headers: `X-Request-ID`, `X-Model-Version`.

### Example

```bash
curl -s -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d @../contracts/examples/request.transfer.json
```

## 3. `GET /v1/model-info`

Returns JSON such as:

```json
{
  "model_version": "v1",
  "trained_at": "2026-10-20T09:30:00Z",
  "dataset": "PaySim",
  "feature_list": ["amount", "amount_log"],
  "scored_types": ["TRANSFER", "CASH_OUT"],
  "thresholds": {"review": 0.5, "block": 0.9},
  "metrics": {"val_pr_auc": 0.0, "test_pr_auc": 0.0},
  "contract_version": "1.0"
}
```

(Values above are placeholders; real values come from the model directory.)

## 4. Health endpoints

| Path | 200 when | Non-200 |
|---|---|---|
| `/health/live` | The process is running | none (if it does not respond, the container is dead) |
| `/health/ready` | Model loaded, feature list matches the code, thresholds valid | 503 with a reason string |

Orchestrators (Docker, Kubernetes) should use `live` for restarts and `ready` for routing traffic.

## 5. Performance and client guidance

- Target p95 under 50 ms, p99 under 100 ms (architecture doc).
- Clients should use a **timeout of about 150 ms** and fall back to rules on timeout.
- The endpoint is idempotent; retries on timeout are safe.

## 6. Versioning rules

- Breaking contract change: new path prefix `/v2`, old one kept for a deprecation period.
- Additive optional fields: stay on `/v1` and bump `schema_version` to `1.1` (contract process).
- The service rejects an unknown `schema_version` with `UNSUPPORTED_SCHEMA_VERSION`.

## 7. Security notes (scope for v1)

- Intended for internal service-to-service traffic only; not exposed publicly.
- Optional shared-secret header for a basic demonstration of service auth. Real deployments would use mTLS or an API gateway.
- Never log account IDs in clear text; log a short hash. Never return stack traces.
