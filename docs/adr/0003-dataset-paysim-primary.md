# ADR-0003: PaySim as the primary dataset; Sparkov as the backup; IBM AML as a later extension

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Swayam

## Context

The system handles account-to-account transfers, and the model needs account identifiers (to build history features), a transaction type, an amount, and a time axis. Public real banking data does not exist, so synthetic data is required. A web survey of public fraud datasets (see `fraud-ml-service/docs/01-dataset-plan.md`) found:

- **PaySim** has sender/receiver account IDs, type, amount, hourly time steps, and about 6.3 million rows. It has known quirks (see ADR-0005).
- **Sparkov** (simulated card transactions) has customers, merchants, geography, and timestamps, and its generator is configurable and MIT-licensed.
- **IBM AML (AMLworld)** models bank-to-bank transfers and laundering patterns; it is an AML problem rather than payment fraud.
- The ULB credit-card dataset has anonymised features and no accounts; IEEE-CIS is e-commerce with anonymised features; BAF is account-opening fraud. None map to the contract.

## Decision

1. Use **PaySim** as the primary training dataset for v1.
2. Keep **Sparkov** as the documented backup (and as the route to card-payment scoring later).
3. Treat **IBM AML** as an optional later extension (graph or laundering-pattern service), not part of v1.

Backup is triggered by the criteria in the dataset plan, evaluated at the end of Phase 1.

## Consequences

- **Positive:** the data maps directly onto the contract; the project story ("transfers between accounts") matches the banking domain.
- **Negative:** PaySim is synthetic and simpler than real fraud; scores must not be presented as real-world accuracy. With balance columns excluded (ADR-0005) the available signal is narrower, so engineered history features matter more.
- **Follow-ups:** document dataset limitations in the model card; keep the feature code dataset-agnostic where possible so a Sparkov switch is a contained change.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| ULB credit card dataset | Anonymised features and no account IDs |
| IEEE-CIS | Anonymised, e-commerce focused, heavy identity-table joins |
| Generate our own data from scratch | Time cost; may be considered later as an extension |

## References

- `fraud-ml-service/docs/01-dataset-plan.md`
