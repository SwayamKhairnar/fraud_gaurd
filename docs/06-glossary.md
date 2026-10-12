# 06. Glossary

Plain-language definitions of the terms used across the docs.

## Fraud and banking

| Term | Meaning |
|---|---|
| Fraud | A transaction the account owner did not genuinely authorise, or that moves money for illegal purposes |
| Velocity | How fast an account is transacting (how many transactions or how much money in a recent window) |
| Fan-in | Many different senders paying one receiver in a short time |
| Cash-out | Converting account balance into cash |
| SAGA | A pattern for completing a multi-service transaction using a sequence of local steps with compensating actions on failure |
| Idempotency | Doing the same request twice has the same effect as doing it once |
| Shadow mode | Running a new model or rule alongside the live decision, logging what it would have done, without enforcing it |

## Machine learning

| Term | Meaning |
|---|---|
| Feature | An input number or category the model uses (for example `amount` or `sender_txn_count_24h`) |
| Label | The correct answer in the data (`is_fraud` = 1 or 0) |
| Class imbalance | Fraud is very rare (about 0.1% of PaySim), so a model that always says "not fraud" looks 99.9% accurate and is useless |
| Precision | Of the transactions we flagged as fraud, the share that really were fraud. High precision means few false alarms |
| Recall | Of all real fraud, the share we caught. High recall means few missed frauds |
| PR curve / PR-AUC | Precision plotted against recall across all thresholds, and the area under it. The main metric here because it works well with rare positives |
| Threshold | The score cut-off for acting (for example block at 0.90 and above) |
| Calibration | Whether a score of 0.8 really means "about 80% of such cases are fraud" |
| Overfitting | A model that memorised the training data and does worse on new data |
| Data leakage | Information in the features that would not be available at prediction time, making results look better than they are |
| Point-in-time correct | Features for a transaction are computed using only data from before that transaction |
| Training-serving skew | Features computed one way during training and another way in production, silently breaking the model |
| Drift | The real-world data changes so the model's inputs or outputs look different from training |
| PSI (Population Stability Index) | A number measuring how much a distribution has shifted. Above 0.2 is a common "investigate" level |
| Model artifact | The saved files that make up a trained model (model file, feature list, metrics, thresholds) |
| Baseline | A simple model used as the yardstick the real model must beat |
| LightGBM | A fast gradient-boosted decision tree library, strong for tabular data like this |
| Reason codes | Short human-readable tags explaining why a transaction scored high |

## Services and operations

| Term | Meaning |
|---|---|
| Contract | The agreed request/response format between two services |
| Health check (liveness / readiness) | Liveness: the process is running. Readiness: it is able to serve (for example, the model is loaded) |
| Circuit breaker | A guard that stops calling a failing service for a while and uses a fallback instead |
| p95 / p99 latency | The time within which 95% / 99% of requests complete |
| SLO | A target for a service level, such as "99% of predictions under 100 ms" |
| ADR | Architecture Decision Record: a short document capturing one design decision and its trade-offs |
