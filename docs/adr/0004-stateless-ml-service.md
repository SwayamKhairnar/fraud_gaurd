# ADR-0004: Stateless ML service; the caller supplies history features in `context`

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Swayam

## Context

Strong fraud features depend on account history (how many transactions in the last hour, is this a new receiver). That history has to live somewhere in production. The system already plans Redis next to the fraud-detection service.

## Decision

`fraud-ml-service` is **stateless**. It does not talk to Redis or any database. The caller (`fraud-detection-service`) computes the history features and sends them in the request under `context`. The ML service only derives per-request features (such as hour of day, amount ratios) from the request itself.

## Consequences

- **Positive:** the ML service scales horizontally with no shared state; it is simple to test, containerise, and replace; responsibilities stay clear (history belongs to the service that owns Redis).
- **Negative:** the two sides must compute features **identically** or the model degrades silently (training-serving skew). The exact definitions are therefore fixed in `fraud-ml-service/docs/02-feature-spec.md` and a parity check is required (see testing strategy).
- **Follow-ups:** a reference implementation of the context features lives in `fraud-ml-service/app/features/` and is used by the mock client and training; ADR-0006 fixes the window semantics.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| ML service reads Redis directly | Couples the ML service to another service's data store; harder to test and scale |
| ML service keeps its own history store | Duplicates state and doubles the write path |
| Send raw event history with each request | Large payloads, higher latency, and the caller still needs the history |
