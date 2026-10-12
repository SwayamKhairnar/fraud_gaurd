# 01. Dataset Plan

Decision record: `docs/adr/0003-dataset-paysim-primary.md`. Balance-column decision: `docs/adr/0005-exclude-balance-columns.md`.

## 1. Requirements the dataset must meet

| Need | Why |
|---|---|
| Sender and receiver account IDs | To build history (velocity, new receiver, fan-in) features |
| Transaction type and amount | Core inputs |
| A time axis with ordering | Point-in-time features and a time-based split |
| Labelled fraud | Supervised training |
| Enough rows and fraud cases | At least a few thousand fraud examples |
| Clear licence / free access | Safe to use in a portfolio project |

## 2. Candidates (summary of the survey)

| Dataset | Fit | Verdict |
|---|---|---|
| **PaySim** (Kaggle `ealaxi/paysim1`) | Accounts, type, amount, hourly steps; about 6.3M rows; about 0.13% fraud; fraud only in TRANSFER and CASH_OUT | **Primary** |
| **Sparkov** (Kaggle `kartik2112/fraud-detection`, plus an MIT-licensed generator) | Card transactions, customers, merchants, geography, timestamps; about 1.3M rows | **Backup** and card-payment extension |
| **IBM AML / AMLworld** (Kaggle `ealtman2019/ibm-transactions-for-anti-money-laundering-aml`) | Bank-to-bank transfers with laundering labels; an AML problem, not fraud | Later extension only |
| ULB credit card (Kaggle) | Anonymised PCA features, two days, no accounts | Rejected |
| IEEE-CIS (Kaggle) | Anonymised e-commerce features, identity-table joins | Rejected |
| BAF (Feedzai) | Account-opening fraud, not payments | Rejected |

Synthetic data caveat: results on simulated data show the pipeline works. They are **not** evidence of real-world accuracy. The model card must say this.

## 3. Primary dataset: PaySim

### Source and files
- Kaggle: `ealaxi/paysim1` (download in `docs/03-dev-environment.md`).
- Expected file: one CSV log (about 6.3 million rows, 11 columns). Verify the exact name after download.

### Columns

| Column | Meaning | Use in v1 |
|---|---|---|
| `step` | Hour index, 1 to 744 (one month) | Time axis, split, hour buckets |
| `type` | CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER | Filter and feature |
| `amount` | Transaction amount | Feature |
| `nameOrig` | Sender account ID | History features (not a model input) |
| `oldbalanceOrg` | Sender balance before | **Excluded** (ADR-0005) |
| `newbalanceOrig` | Sender balance after | **Excluded** |
| `nameDest` | Receiver account ID | History features (not a model input) |
| `oldbalanceDest` | Receiver balance before | **Excluded** |
| `newbalanceDest` | Receiver balance after | **Excluded** |
| `isFraud` | Label | Target |
| `isFlaggedFraud` | Simulator's own simple rule flag | **Excluded** |

### Known characteristics (to confirm in EDA)
- Fraud occurs only in `TRANSFER` and `CASH_OUT`. Train on those two types; other types return `scored_by_model=false`.
- Fraud rate is about 0.13% overall (higher within the two modelled types).
- Account IDs starting with `M` are merchants; they appear as receivers of PAYMENT.
- The dataset's own documentation says its balance columns must not be used for fraud detection.

### Memory-friendly loading
Use explicit dtypes (for example `step` as int16, `amount` as float32, `type` as category, IDs as strings) and filter to the two modelled types immediately after loading. Save the filtered table as Parquet in `data/processed/` for fast reloads.

## 4. Time-based split

Fraud models must be evaluated on the **future**, not on randomly shuffled rows.

| Split | Steps (initial proposal) | Purpose |
|---|---|---|
| Train | 1 to 500 | Fit the model |
| Validation | 501 to 620 | Choose model settings and thresholds |
| Test | 621 to 744 | One-time final evaluation |

Checks before accepting the split (Phase 1):
- [ ] Each split contains at least 500 fraud cases (adjust boundaries if not)
- [ ] Fraud rate per split is of a similar order of magnitude
- [ ] History features for validation/test rows use history from earlier steps, including steps in earlier splits (history is not truncated at the split boundary, only the **labels** are split)

## 5. Backup plan

### Backup triggers (evaluate at the end of Phase 1 and again after the baseline in Phase 3)

Switch to Sparkov (or add it) if **any** of these holds:

| Trigger | Threshold |
|---|---|
| EDA shows too few fraud cases per split | Fewer than 500 in validation or test after reasonable boundary changes |
| Baseline plus LightGBM cannot beat a trivial rule (for example "type in TRANSFER/CASH_OUT and amount above a high cut-off") on PR-AUC by a meaningful margin | After one time-boxed feature iteration (max half a session) |
| History features carry no signal at all (ablation shows no gain over per-transaction features) | Same time-box |
| A leakage problem cannot be resolved | Any time |

Do **not** switch merely because the numbers look lower than tutorials show; those often use the excluded balance columns.

### What a switch to Sparkov involves
1. Download `kartik2112/fraud-detection` (verify the file names after download) or generate your own data with the Sparkov generator.
2. Map fields: customer (account), merchant (receiver), category, amount, timestamp, location.
3. Contract change to **v1.1** (additive): optional merchant and geo fields, new context features such as distance from home and merchant-category history; see `contracts/README.md` for the change process.
4. New feature spec section and a new model version (`v2`; model versions must match the `vN` pattern, so the dataset is recorded in `metadata.json`, not in the version name).
5. The service architecture does not change.

### Last-resort fallback
Write a small simulator of your own that emits events in the contract format with injected fraud patterns (rapid repeated transfers, new receivers with large amounts, fan-in to one account). It is also useful as the mock traffic generator.

## 6. Extensions (not part of v1)

| Extension | Dataset | What it adds |
|---|---|---|
| Card payment scoring | Sparkov | Merchant category and geography features, a second payment type |
| AML / suspicious flow detection | IBM AML | A separate graph-based service: fan-in, fan-out, cycles |

## 7. Data handling rules

- Raw data and processed tables are never committed (`.gitignore` enforces it).
- Record the dataset name, source URL, download date, and file checksum in the model's `metadata.json`.
- Respect each dataset's licence and cite the original paper where the licence asks for it (PaySim: Lopez-Rojas, Elmir, Axelsson, "PaySim: A financial mobile money simulator for fraud detection").

## 8. Sources used in the survey

- PaySim on Kaggle (`ealaxi/paysim1`) and its description
- Sparkov generator (GitHub `namebrandon/Sparkov_Data_Generation`, MIT licence) and its Kaggle dataset
- AMLworld paper "Realistic Synthetic Financial Transactions for Anti-Money Laundering Models" and its Kaggle datasets
- Fraud Dataset Benchmark paper (comparison of public fraud datasets)
