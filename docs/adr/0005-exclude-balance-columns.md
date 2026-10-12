# ADR-0005: Exclude PaySim balance columns and `isFlaggedFraud` from model features

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Swayam

## Context

The PaySim dataset documentation states that transactions detected as fraud are cancelled, and for that reason the four balance columns (`oldbalanceOrg`, `newbalanceOrig`, `oldbalanceDest`, `newbalanceDest`) must not be used for fraud detection: their values reflect what happened *after* the fraud outcome and so leak the label. The dataset also contains `isFlaggedFraud`, a flag produced by the simulator's own simple rule, which would not be an independent signal.

An earlier planning note suggested using the "before" balances. That suggestion is **withdrawn** in favour of the dataset author's guidance.

## Decision

The model will not use any of the four balance columns nor `isFlaggedFraud`. Balance fields stay in the contract as **optional, accepted-but-ignored** inputs (`sender_balance_before`, `receiver_balance_before`) so that a future dataset or model version can use them without a breaking change.

A one-off **ablation experiment** (with vs without the balance columns) is allowed during training for understanding only. Its numbers must never be reported as model performance.

## Consequences

- **Positive:** honest evaluation; no hidden leakage; the model's inputs match what a real system can know at decision time.
- **Negative:** headline metrics will be lower and harder to reach than in tutorials that use the balances; more reliance on engineered history features.
- **Follow-ups:** the model card must state this exclusion and the PaySim limitations.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| Use "before" balances only | Contradicts the dataset author's guidance and risks subtle leakage |
| Use all balances | Obvious leakage; metrics would be misleading |

## References

- PaySim dataset description (Kaggle), see `fraud-ml-service/docs/01-dataset-plan.md`
