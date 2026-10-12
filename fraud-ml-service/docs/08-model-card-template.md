# 08. Model Card Template

Copy this file to `artifacts/models/<version>/MODEL_CARD.md` (or `docs/model-cards/<version>.md`) for every trained version and fill in every section. Be honest: the limitations section is the most valuable part.

---

# Model Card: fraud-ml-service `vN`

## 1. Model details

| Field | Value |
|---|---|
| Model version | vN |
| Date trained | |
| Model type | (for example LightGBM gradient-boosted trees) |
| Library versions | python, lightgbm, scikit-learn, pandas, numpy |
| Code version | git commit hash |
| Contract version | 1.0 |
| Owner | Swayam |

## 2. Intended use

- **Intended:** scoring TRANSFER and CASH_OUT transactions in the digital banking portfolio project, producing a risk score and a recommended action.
- **Out of scope:** real banking decisions; any use with real customer data; transaction types other than TRANSFER and CASH_OUT (these return `scored_by_model=false`).

## 3. Data

| Item | Value |
|---|---|
| Dataset | PaySim (synthetic mobile-money log) |
| Source / download date / checksum | |
| Rows total / used | |
| Fraud rate (overall / used) | |
| Time split | train steps ..., validation steps ..., test steps ... |
| Excluded columns | `oldbalanceOrg`, `newbalanceOrig`, `oldbalanceDest`, `newbalanceDest`, `isFlaggedFraud` (ADR-0005) |

## 4. Features

Reference: `docs/02-feature-spec.md`. List the final ordered features and note any that were dropped during development and why.

## 5. Training procedure

- Imbalance handling:
- Hyperparameter search (space, trials, time spent):
- Early stopping criterion:
- Random seed:
- Calibration applied: yes / no

## 6. Evaluation

### Metrics

| Metric | Baseline (rule) | Baseline (logistic regression) | This model: validation | This model: test |
|---|---|---|---|---|
| PR-AUC | | | | |
| Recall at precision >= 0.90 | | | | |
| Recall at precision >= 0.50 | | | | |
| Precision at recall >= 0.80 | | | | |
| Fraud amount caught (%) | | | | |

### Operating points

| Threshold | Value | Precision | Recall | Share of traffic | Meaning |
|---|---|---|---|---|---|
| `review_threshold` | | | | | |
| `block_threshold` | | | | | |

Confusion matrix at the chosen thresholds (counts):

|  | Predicted ALLOW | Predicted REVIEW | Predicted BLOCK |
|---|---|---|---|
| Actually legitimate | | | |
| Actually fraud | | | |

### Serving performance

| Metric | Value | Test conditions |
|---|---|---|
| p50 / p95 / p99 latency (single request) | | machine, concurrency |
| Throughput | | |

## 7. Leakage and sanity checks performed

- [ ] Shuffled-label test: validation PR-AUC fell to about the base rate
- [ ] No excluded columns used
- [ ] Manual verification of point-in-time features on a sample
- [ ] Parity test passed

## 8. Limitations and risks

State plainly, for example:
- The data is synthetic; metrics do not predict real-world accuracy.
- Fraud in PaySim follows simple simulated patterns; a real attacker would adapt.
- Only two transaction types are modelled.
- Features depend on the caller computing history identically; skew silently harms accuracy.
- Reason codes are rule-based approximations, not true model explanations.
- (Add anything discovered during the work.)

## 9. Monitoring plan

Metrics, drift checks, and alert thresholds to watch for this version: see `docs/05-observability.md`. Specific expectations for this version (decision mix at the chosen thresholds, score distribution summary):

## 10. Change log

| Version | Date | Change | Reason |
|---|---|---|---|
| vN | | initial | |
