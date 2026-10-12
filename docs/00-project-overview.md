# 00. Project Overview

## 1. What this project is

A digital banking backend, split into microservices, where every payment is checked for fraud in real time before it is allowed to complete. Fraud checking combines **business rules** with a **machine-learning risk score** served by a dedicated ML microservice.

It is inspired by a public tutorial on bank fraud detection with a Kafka/Redis/Spring Boot stack. This project deliberately **extends** that idea rather than copying it (see section 6).

## 2. Goals

1. **Primary:** a clean, working microservices system that shows real backend engineering (service boundaries, async messaging, resilience, observability) and can be explained confidently in placement interviews.
2. **Secondary:** a production-style ML service: trained model, versioned artifacts, stable API, metrics, container image, and clear integration rules.
3. **Tertiary:** a platform for demonstrating system design concepts (caching, idempotency, circuit breaking, event-driven flows, SAGA, backpressure, observability).

## 3. Non-goals

- Not a real bank: no real money, no real personal data. All data is synthetic.
- Not ML research: the model only needs to be sound, honestly evaluated, and well integrated. Chasing the last 1% of accuracy is out of scope.
- Not a full product: no polished UI is required for the ML phase.

## 4. Success criteria

The project is a success when:

- [ ] A transfer submitted to the system is scored by the ML service and gets an ALLOW / REVIEW / BLOCK decision end to end.
- [ ] The ML service can be started with one command (`docker compose up`) and passes its health checks.
- [ ] Each service can be developed and tested without the others running (using the contract and mock clients).
- [ ] There is a dashboard showing request rate, latency, error rate, and fraud-score distribution.
- [ ] A new reader can understand the system from `docs/` in under 30 minutes.
- [ ] Each major design choice has an ADR explaining the trade-off.

## 5. Constraints

| Constraint | Value | Consequence |
|---|---|---|
| Time budget | about 1.5 months at about 2 full days per week (about 12 working days) | ML phase must be time-boxed (see roadmap) |
| ML background | Limited, learning as we go | Prefer simple, explainable models; document the "why" |
| Focus | Systems and backend first; ML is complementary | ML service must be a clean black box behind a contract |
| Infrastructure | Laptop-class machine, Docker | No GPUs, no cloud dependency for v1 |

## 6. How this differs from the reference tutorial

| Idea | Phase | Notes |
|---|---|---|
| Real ML model behind a versioned API instead of only rules | ML phase | Core of this document set |
| Contract-first design with JSON Schema + contract tests | ML phase | Prevents integration surprises |
| Hour-bucketed velocity features that match offline and online | ML phase | See ADR-0006 |
| Model versioning and rollback | ML phase | `artifacts/models/CURRENT` |
| Prometheus metrics + Grafana dashboard for the ML service | ML phase | `fraud-ml-service/docs/05-observability.md` |
| Shadow mode (score but do not enforce) before trusting the model | Later | Lives in `fraud-detection-service` |
| Circuit breaker + fallback to rules when ML is down | Later | `fraud-ml-service/docs/10-integration-guide.md` |
| Idempotent transaction handling | Later | txn_id as idempotency key |
| Feedback loop (confirmed fraud labels back to training data) | Later | `fraud.feedback` topic |
| Optional: AML graph service or card-payment scoring | Stretch | See dataset plan |

## 7. Services

| Service | Responsibility | Owns |
|---|---|---|
| `account-service` | Accounts and balances | Account DB |
| `transaction-service` | Accepts payments, runs the SAGA, publishes events | Transaction DB |
| `fraud-detection-service` | Orchestrator: maintains velocity counters, applies rules, calls ML, decides | Redis counters, decision log |
| `fraud-ml-service` | Scores a transaction (stateless) | Model artifacts only |
| `notification-service` | Sends alerts and confirmations | Notification log |

## 8. Technology stack

| Layer | Choice |
|---|---|
| Core services | Java 17+ / Spring Boot |
| ML service | Python 3.11, FastAPI, scikit-learn, LightGBM |
| Messaging | Kafka |
| Cache and counters | Redis |
| Databases | PostgreSQL |
| Observability | Prometheus, Grafana, structured JSON logs |
| Packaging | Docker, docker compose |
