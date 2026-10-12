# infra

Local infrastructure for the whole system. Right now it only runs the ML service and optional monitoring; Kafka, Redis, PostgreSQL, and the Java services are added as those phases begin.

## Run

```bash
cd infra
docker compose up --build                       # ML service only
docker compose --profile monitoring up --build  # plus Prometheus (9090) and Grafana (3000)
```

The ML service needs a trained model mounted from `fraud-ml-service/artifacts/models/` (it must contain `CURRENT` and a version directory). Without one the container starts but `/health/ready` returns 503 by design.

## Files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Service definitions; `monitoring` profile for Prometheus and Grafana |
| `prometheus/prometheus.yml` | Scrape configuration |

## Grafana setup (Phase 5)

1. Open `http://localhost:3000`, add a Prometheus data source pointing at `http://prometheus:9090`.
2. Build the dashboard described in `fraud-ml-service/docs/05-observability.md`.
3. Export it as JSON and save it under `infra/grafana/dashboards/` so it is versioned.

## Later additions (planned)

Kafka and Zookeeper/KRaft, Redis, PostgreSQL, and one container per Java service, all on the same compose network.
