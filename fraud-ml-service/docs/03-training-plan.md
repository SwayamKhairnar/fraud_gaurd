# 03. Training Plan

Step-by-step plan from raw data to a promoted model. Each step lists its **inputs, outputs, and a done-check**. Scripts named here are to be created during Phases 2 and 3.

## 0. Ground rules

- Reproducible: fixed random seed (`42`), all settings in `config/training.yaml` (to be created), library versions saved with the model.
- Time-based split only (dataset plan, section 4).
- Never touch the test split until the very end (once).
- Excluded columns stay excluded (ADR-0005).
- Time-box: this plan should fit in about 2 sessions (Phases 2 and 3). Cut list in the roadmap.

## 1. Environment and data

| | |
|---|---|
| Input | Downloaded PaySim CSV in `data/raw/` |
| Script | `training/prepare_data.py` |
| Output | `data/processed/paysim_clean.parquet` (typed columns, event-order index) |
| Done-check | Row count matches the source; no duplicate event indices; dtypes as specified |

## 2. Exploratory analysis (notebook)

`notebooks/01_eda.ipynb`

Questions to answer (write the answers at the top of the notebook):
1. Fraud rate overall, by type, and by step. Any steps with unusual spikes?
2. Distribution of `amount` for fraud vs non-fraud.
3. How many transactions per sender account? Per receiver?
4. Do fraud receivers repeat? Is there any visible fan-in pattern?
5. Fraud counts per candidate split (dataset plan checks).

Decision at the end: PaySim go / no-go (backup triggers in the dataset plan).

## 3. Build the context features (offline)

| | |
|---|---|
| Input | `paysim_clean.parquet` (**all** types, full log) |
| Script | `training/build_features.py` |
| Output | `data/processed/features.parquet` containing the model feature list, label, `step`, and split name |
| Rules | Follow `02-feature-spec.md` exactly; compute history on all types, then filter to TRANSFER and CASH_OUT |
| Done-check | Unit tests green; parity test green; null counts match the spec (`sender_avg_amount_30d` may be null, nothing else) |

Implementation hint: the full log has about 6.3 million rows, so a Python loop per row is too slow. Sort by `(step, original index)`, then build per-account hourly aggregates (group by account and `step`) and combine them with cumulative sums and a window over the previous 23 / 719 steps, subtracting the current row's own contribution so it is excluded. Keep `app/features/context.py` (the simple streaming version) as the **reference**: it may be slow, but it defines correct behaviour, and the parity test proves the fast offline version matches it on a sample.

Leakage checks (all must pass):
- [ ] Shuffle the labels in the training set and retrain once: PR-AUC on validation should fall to about the base fraud rate.
- [ ] No feature uses the label, balances, or `isFlaggedFraud`.
- [ ] For a sample of 100 rows, manually verify the features were computed using only earlier rows.

## 4. Baselines

| Baseline | Purpose |
|---|---|
| Trivial rule: flag if `type` is TRANSFER/CASH_OUT and `amount` is above a high percentile | The "any model must beat this" yardstick |
| Logistic regression with class weighting on the standardised features | Simple, explainable model |

Script: `training/train.py --model baseline`
Output: metrics saved under `reports/` (to be created) and a short table in the notebook.

## 5. Main model: LightGBM

| | |
|---|---|
| Model | `LGBMClassifier`, tree-based, handles nulls natively |
| Imbalance handling | `scale_pos_weight` (negatives / positives) or `class_weight`; **do not** use SMOTE or oversampling first (they complicate point-in-time correctness) |
| Early stopping | On the validation split's PR-AUC |
| Tuning | One small, time-limited random search (for example 20 trials: `num_leaves`, `learning_rate`, `min_child_samples`, `subsample`, `colsample_bytree`, `reg_lambda`). Stop after 30 minutes |
| Seed | 42 |

Script: `training/train.py --model lightgbm`

## 6. Evaluation

Primary metric: **PR-AUC** on the validation split. Report on the test split only at the end.

| Metric | Why |
|---|---|
| PR-AUC | Robust for rare positives |
| Recall at precision >= 0.90 and >= 0.50 | Business-style operating points |
| Precision at recall >= 0.80 | The cost of catching most fraud |
| Confusion matrix at the chosen thresholds | Concrete counts of caught, missed, and false alarms |
| Fraud amount caught (sum of amounts of true positives / total fraud amount) | Value-weighted view |
| Review volume (share of transactions sent to REVIEW) | Operational cost |
| Latency of 1,000 single-row predictions (p50, p95, p99) | Serving feasibility |

Plots (saved to `reports/figures/`): PR curve, score histograms for fraud and non-fraud, feature importance.

Sanity interpretations (write them in the model card):
- If PR-AUC is near-perfect (above about 0.99), suspect leakage and re-run the leakage checks.
- If the model does not beat the trivial rule, trigger the dataset backup review.

## 7. Threshold selection

Use the **validation** set. Starting policy (adjust with evidence):

| Threshold | Policy |
|---|---|
| `block_threshold` | Highest recall subject to precision >= 0.90 |
| `review_threshold` | Lowest value such that review volume is at most 1% of scored transactions, and recall (BLOCK + REVIEW) is as high as possible |

Save to the model directory's `thresholds.yaml`. Operational overrides can be put in `config/thresholds.yaml` without retraining.

Optional (cut if short on time): probability calibration with isotonic regression fitted on the validation set.

## 8. Final test evaluation

Run once on the test split with the chosen model and thresholds. Record the numbers in `metrics.json` and the model card. If results are far below validation, investigate drift between splits rather than re-tuning on the test set.

## 9. Export artifacts and versioning

Layout (ADR-0007):

```
artifacts/models/
├── CURRENT                  <- text file containing e.g. "v1"
└── v1/
    ├── model.joblib         <- the trained model (git-ignored binary)
    ├── feature_list.json    <- ordered feature names
    ├── metadata.json        <- training details (see below)
    ├── metrics.json         <- validation and test metrics
    └── thresholds.yaml      <- review_threshold, block_threshold
```

`metadata.json` must contain: `model_version`, `trained_at`, `dataset` (name, source URL, download date, checksum), `split_boundaries`, `feature_list_hash`, `random_seed`, `library_versions` (python, lightgbm, scikit-learn, pandas, numpy), `reason_code_cutoffs`, `git_commit`.

Script: `training/export_artifacts.py`

Rules:
- A version directory is **immutable** after export. Retraining creates `v2`.
- Never delete the previous version until the new one has run cleanly.
- Promote by writing the new version name into `CURRENT`; roll back by writing the old one.

## 10. Promotion gate (all must be true)

- [ ] Beats the trivial rule and the logistic-regression baseline on validation PR-AUC
- [ ] Leakage checks passed
- [ ] Artifacts load in the service and pass the model smoke test
- [ ] p99 single-row latency within target (architecture doc)
- [ ] Model card completed with honest limitations
- [ ] `feature_list.json` equals the feature spec's list

## 11. Retraining (later)

Triggers and process are in `docs/05-maintenance.md`. A retraining run repeats steps 3 to 10 with new data and a new version number; the pipeline scripts must be re-runnable end to end with one command (`make train`).

## 12. Time plan inside the two sessions

| Block | Content |
|---|---|
| Session A, part 1 | Steps 1 and 2 (data and EDA) |
| Session A, part 2 | Step 3 (features, tests, parity) |
| Session B, part 1 | Steps 4 and 5 (baselines, LightGBM) |
| Session B, part 2 | Steps 6 to 9 (evaluation, thresholds, export, model card) |
