# Digital Banking Fraud Detection System

A microservices digital banking platform with **real-time fraud detection on payments**. It is built to practise and demonstrate backend engineering: service boundaries, contract-first design, event-driven flows, resilience, and observability, with a production-style ML scoring service at the centre of the fraud pipeline.

> **Current focus:** build and finish the `fraud-ml-service` (the ML layer) first, behind a frozen contract, so the other services can be built against it afterwards.

## Status

| Component | Status |
|---|---|
| `contracts/` (ML request/response schemas) | Draft v1.0 (freeze at end of Phase 1) |
| `fraud-ml-service` | Phase 0 scaffold done. Next: environment + EDA |
| `account-service` | Not started |
| `transaction-service` | Not started |
| `fraud-detection-service` (orchestrator: rules + ML score) | Not started |
| `notification-service` | Not started |
| `infra` (Kafka, Redis, Postgres, Prometheus, Grafana) | Not started |

## Repository layout

```
digital-banking-fraud/
├── README.md                     <- you are here
├── CHANGELOG.md                  <- project-level changes
├── docs/                         <- project-wide documentation
│   ├── 00-project-overview.md    <- goals, scope, success criteria
│   ├── 01-architecture.md        <- services, flows, failure handling
│   ├── 02-roadmap.md             <- phased plan with checklists
│   ├── 03-dev-environment.md     <- how to set up your machine
│   ├── 04-conventions.md         <- naming, git, versioning, code style
│   ├── 05-maintenance.md         <- routines, retrain triggers, change process
│   ├── 06-glossary.md            <- plain-language ML + fraud terms
│   └── adr/                      <- architecture decision records
├── contracts/                    <- the shared boundary between services
│   ├── predict-request.schema.json
│   ├── predict-response.schema.json
│   ├── error.schema.json
│   └── examples/
├── infra/                        <- docker-compose and (later) monitoring config
└── fraud-ml-service/             <- the ML microservice (current focus)
```

## Where to start

1. Read `docs/00-project-overview.md`, then `docs/01-architecture.md`.
2. Set up your machine: `docs/03-dev-environment.md`.
3. Work through `docs/02-roadmap.md` from Phase 0.
4. For everything about the ML service: `fraud-ml-service/README.md`.

## Working agreements (short version)

- **Contract first.** Services talk through the schemas in `contracts/`. No service reads another service's database or imports its code.
- **Decisions are written down** as ADRs in `docs/adr/`.
- **Everything is versioned**: contracts, models, and services (semantic versioning, see `docs/04-conventions.md`).
- **Nothing is "done"** until it meets the Definition of Done for that component.
