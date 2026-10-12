# ADR-0001: Build the ML microservice first, as a self-contained boundary

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Swayam

## Context

The project has several services (account, transaction, fraud-detection, notification) plus the ML scoring service. The fraud-detection pipeline depends on the ML service, but the ML service does not depend on any of the others: it takes a transaction in and returns a risk score. The ML work also has the highest uncertainty (data choice, feature design, model quality), and the author has limited ML background.

Time budget is about 12 working days in total, so ordering matters.

## Decision

We will build and finish `fraud-ml-service` first, behind a frozen contract and with a mock client, before starting the other services. The service must be runnable and testable entirely on its own.

## Consequences

- **Positive:** the riskiest unknown is resolved early; other services can integrate against a real, running service instead of guesses; the mock client lets everything else be developed independently.
- **Negative:** about half of the available time goes to the ML phase; no end-to-end banking demo until later phases. Mitigated by strict time-boxes in `docs/02-roadmap.md`.
- **Follow-ups:** contract must be frozen at the end of Phase 1; integration guide must exist before hand-off.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| Build all services first, ML last | The contract and features would be guessed; late discovery of ML problems could invalidate earlier work |
| Build a rules-only fraud service and add ML later | Delays the learning goal and weakens the project story; rules remain part of the later orchestrator anyway |
| Build thin stubs of every service in parallel | Splits attention across too many things for a solo developer with limited days |
