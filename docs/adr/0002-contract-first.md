# ADR-0002: Contract-first integration using JSON Schema

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Swayam

## Context

The ML service (Python) and the fraud-detection service (Java) will be built at different times by the same person. The most common failure in this setup is the two sides silently disagreeing about field names, units, or optionality.

## Decision

The request, response, and error formats are defined as JSON Schema (draft 2020-12) files in `contracts/`, with example payloads. They are the single source of truth. The ML service's Pydantic models must match the schemas, enforced by an automated contract test. The schemas are **strict** in v1: unknown top-level fields are rejected; a free-form `metadata` object is the only extension point.

## Consequences

- **Positive:** errors surface at the boundary with clear messages; Java and Python can both validate or generate code from the same files; examples double as test fixtures and documentation.
- **Negative:** every field change needs an edit in several places (schema, Pydantic model, docs, examples). The contract test and the change process in `docs/05-maintenance.md` keep this manageable.
- **Follow-ups:** `contracts/README.md` documents the change process and versioning; `tests/contract/` must validate all examples.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| OpenAPI as the source of truth | Good option, but heavier; the service is small. FastAPI will still generate an OpenAPI document, which can be compared against the schemas |
| Protobuf / gRPC | Adds tooling cost and makes manual testing harder; REST + JSON is enough for the latency target |
| No formal contract, just documentation | Prone to drift; no automated checks |
