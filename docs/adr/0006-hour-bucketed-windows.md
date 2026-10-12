# ADR-0006: Velocity features use hour-bucketed windows

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Swayam

## Context

Velocity features need time windows ("last 1 hour", "last 24 hours"). PaySim only records time as an integer `step`, where one step is one hour. In production, transactions have exact timestamps. If windows are sliding (exactly 60 minutes back) in production but hour-granular in training, the features differ and the model degrades.

## Decision

All windows are defined on **hour buckets**, where `bucket = floor(timestamp to the hour)` (in training, `bucket = step`).

- `1h` window = the current bucket only
- `24h` window = the current bucket and the previous 23 buckets
- `30d` window = the current bucket and the previous 719 buckets

Only transactions **strictly earlier in event order** than the current one count. In training, event order is `(step, original row order)`. Production uses the same bucket definitions with exact arrival order.

## Consequences

- **Positive:** training and production compute identical definitions. Redis can store counters per account per hour bucket with a TTL (cheap, simple, expiry for free).
- **Negative:** the "1h" window is not a true rolling hour; a transaction at 10:59 sees activity from 10:00 onwards but one at 11:01 does not see 10:59. Accepted as the price of consistency.
- **Follow-ups:** the feature spec gives exact formulas; a parity test replays a dataset sample through the reference implementation and compares to the offline table.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| Sliding exact windows in production, hour-granular in training | Guaranteed skew |
| Simulate sub-hour timestamps in training | Invents precision the data does not have |
| Use only per-request features (no history) | Throws away the strongest signals and the Redis part of the system design |
