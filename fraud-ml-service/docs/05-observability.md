# 05. Observability

Goal: anyone can answer "is the ML service healthy, fast, and behaving as it did when we trained it?" from a dashboard and from logs.

## 1. Three pillars

| Pillar | v1 | Later |
|---|---|---|
| Metrics | Prometheus endpoint `/metrics` | Alert rules, SLO burn rates |
| Logs | Structured JSON on stdout | Central log store (Loki or ELK) |
| Traces | Correlation ID (`X-Request-ID`) propagated and logged | OpenTelemetry distributed tracing |

## 2. Metrics (Prometheus)

Names use the `fraud_ml_` prefix. Labels are kept low-cardinality (never account IDs or txn IDs).

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `fraud_ml_requests_total` | counter | `endpoint`, `status` | Traffic and errors |
| `fraud_ml_request_duration_seconds` | histogram | `endpoint` | Latency percentiles |
| `fraud_ml_predictions_total` | counter | `decision`, `scored_by_model` | Decision mix |
| `fraud_ml_fraud_score` | histogram | none | Score distribution (buckets 0.0, 0.05, ..., 1.0) for drift watching; only for scored requests |
| `fraud_ml_feature_null_total` | counter | `feature` | Unexpected nulls (for example `sender_avg_amount_30d`) |
| `fraud_ml_errors_total` | counter | `code` | Error codes from `error.schema.json` |
| `fraud_ml_model_info` | gauge (value 1) | `model_version` | Which model is live |
| `fraud_ml_model_loaded_timestamp_seconds` | gauge | none | When the model was loaded |

Standard process/Python metrics from the Prometheus client are also exposed.

## 3. Logs

One JSON object per line. Mandatory fields: `timestamp`, `level`, `service`, `request_id`, `message`. For prediction events add `txn_id`, `type`, `model_version`, `fraud_score`, `decision`, `scored_by_model`, `latency_ms`, `reason_codes`, and `sender_hash` and `receiver_hash` (first 8 hex characters of a SHA-256 of the account ID).

Log levels:
- `INFO`: one line per prediction request and per model load
- `WARNING`: validation failures, unexpected nulls
- `ERROR`: model load failure, unhandled exceptions (stack trace in logs only, never in the response)

## 4. Dashboard (Grafana, Phase 5)

Panels:
1. Requests per second by status
2. Latency p50 / p95 / p99
3. Error rate
4. Decisions over time (ALLOW / REVIEW / BLOCK share)
5. Score distribution heatmap or histogram
6. Live model version and load time
7. Feature null counts

## 5. Alerts (rules to define; fire to a log or webhook initially)

| Alert | Condition (initial) | Meaning |
|---|---|---|
| High latency | p99 over 200 ms for 5 minutes | Capacity or slow feature code |
| Elevated errors | error rate over 1% for 5 minutes | Contract mismatch or bug |
| Model not ready | `/health/ready` failing for 1 minute | Model missing or invalid |
| Decision mix shift | BLOCK + REVIEW rate more than 3 standard deviations from the trailing week | Drift or an upstream data issue |
| Score drift | PSI of score distribution versus the training validation distribution above 0.2 | Inputs have shifted; consider retraining |

## 6. Drift monitoring (offline, later)

A small script compares a recent window of logged scores and context features against the training distribution (PSI per feature and for the score) and writes a report. Run it manually first, then on a schedule. See `docs/05-maintenance.md`.

## 7. Integration with other services

- Every call carries `X-Request-ID`; the ML service logs and returns it, so a single transaction can be followed across services.
- The same metric naming style (`<service>_...`) is to be used by every other service.
- One Prometheus and one Grafana in `infra/` scrape all services.

## 8. Implementation notes

- Metrics registry and logging setup live in `app/core/metrics.py` and `app/core/logging.py`.
- The score histogram should use fixed buckets so dashboards stay comparable across versions.
- Instrumentation happens in middleware and in the predictor, not scattered through route code.
