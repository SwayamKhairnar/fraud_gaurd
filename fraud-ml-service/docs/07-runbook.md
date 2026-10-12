# 07. Runbook

Operating the ML service: starting it, checking it, fixing common problems, and changing the model.

## 1. Start and stop

### Local (no Docker)
```bash
cd fraud-ml-service
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # --reload for development only
```

### Docker compose
```bash
cd infra
docker compose up --build -d
docker compose logs -f fraud-ml-service
docker compose down
```

## 2. Quick health check

```bash
curl -s localhost:8000/health/live
curl -s localhost:8000/health/ready
curl -s localhost:8000/v1/model-info
curl -s localhost:8000/metrics | head -n 20
curl -s -X POST localhost:8000/v1/predict -H "Content-Type: application/json" \
     -d @../contracts/examples/request.transfer.json
```

Healthy: `ready` returns 200, `model-info` shows the expected `model_version`, and predict returns a valid response.

## 3. Reading logs

Logs are JSON, one object per line.

```bash
docker compose logs fraud-ml-service | jq -c 'select(.level=="ERROR")'
docker compose logs fraud-ml-service | jq -c 'select(.request_id=="<id>")'
docker compose logs fraud-ml-service | jq -c 'select(.decision=="BLOCK") | {txn_id, fraud_score, reason_codes}'
```

## 4. Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| `/health/ready` is 503, "model not found" | `CURRENT` missing, wrong version name, or volume not mounted | Check `artifacts/models/CURRENT`; check the compose volume path; confirm `MODEL_DIR` |
| `/health/ready` is 503, "feature list mismatch" | Code and model trained with different feature lists | Re-export the model or check out the matching code version; compare `feature_list.json` with `app/features` |
| Startup crash importing LightGBM | Missing OpenMP runtime in the image | Ensure `libgomp1` is installed in the Dockerfile |
| Many 422 responses | Caller sending a payload that violates the contract | Inspect `details` in the error body and the logs; validate the caller's payload against `contracts/` |
| Latency high | Too few workers, cold start, noisy host, slow feature code | Check CPU; run the load test; profile `app/features`; consider `WEB_CONCURRENCY=2` |
| Scores all near 0 or all near 1 | Feature skew (caller computing context differently) or wrong model | Compare caller's context values to the feature spec; run the parity replay; check `model_version` |
| `fraud_ml_feature_null_total` rising for a feature that should never be null | Caller bug | Fix the caller; check the contract rules |
| Memory growth | Large batch of metrics labels or a leak | Check label cardinality; restart; investigate with a memory profiler |
| Container restarts repeatedly | Liveness failing or a crash on startup | `docker compose logs`; run the image manually with `docker run -it` |

## 5. Change the model (promote)

1. Train and export the new version (`artifacts/models/v2/`), fill its model card, run the promotion gate (training plan, section 10).
2. In a staging run (local compose), set `artifacts/models/CURRENT` to `v2`, restart the service, and run the container test and model tests.
3. Compare score distributions of `v1` versus `v2` on the same sample (the decision mix should be explainable).
4. Update `CURRENT` in the real environment and restart.
5. Watch the dashboard for 30 minutes: latency, error rate, decision mix, score distribution.
6. Update `CHANGELOG.md` (Model section).

## 6. Roll back the model

1. Write the previous version name into `artifacts/models/CURRENT` (for example `v1`).
2. Restart the service.
3. Confirm `/v1/model-info` and the dashboard show the old version.
4. Record why in the CHANGELOG and open an issue or ADR if the cause needs a fix.

The previous version directory must still exist; never delete it until the new one has been stable.

## 7. Configuration reference

| Variable | Default | Meaning |
|---|---|---|
| `ML_SERVICE_PORT` | `8000` | Port |
| `MODEL_DIR` | `artifacts/models` | Directory containing `CURRENT` and version folders |
| `LOG_LEVEL` | `INFO` | Log level |
| `API_KEY_ENABLED` | `false` | Require `X-API-Key` |
| `API_KEY` | (empty) | The shared secret when enabled |
| `WEB_CONCURRENCY` | `1` | Uvicorn worker processes |
| `THRESHOLDS_OVERRIDE_PATH` | `config/thresholds.yaml` | Operational thresholds override |

Full list in `.env.example`.

## 8. Incident note template

```
Date/time:
What was seen (symptom, alert, metric):
Impact (who/what was affected):
Cause:
Fix / mitigation:
Follow-up actions (tests, docs, alerts):
```
