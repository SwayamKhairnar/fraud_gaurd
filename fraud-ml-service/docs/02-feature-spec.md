# 02. Feature Specification

The most important document in the ML service. It defines **exactly** how every feature is computed so that training, the ML service, the mock client, and the Java `fraud-detection-service` all agree. Any deviation is training-serving skew. Related: ADR-0004, ADR-0005, ADR-0006.

## 1. Principles

1. **Point-in-time correct:** a feature for transaction *t* uses only transactions strictly earlier than *t*.
2. **Pure functions:** same inputs give the same outputs; no I/O; no global state.
3. **One implementation shared** by training and serving (`app/features/`).
4. **No excluded columns** (balances, `isFlaggedFraud`).
5. **Fixed order:** the model's feature order is stored in `feature_list.json` and checked at load time.

## 2. Event order and time buckets

- `bucket(t)`: in training, `bucket = step`. In production, `bucket = floor(timestamp to the hour)` expressed as an hour number.
- **Event order** for "earlier than": training uses `(step, original row index)`. Production uses arrival order at the fraud-detection service.
- Windows:

| Name | Buckets included |
|---|---|
| `1h` | current bucket only |
| `24h` | current bucket and the previous 23 |
| `30d` | current bucket and the previous 719 |

"Earlier" always means earlier in event order **and** inside the window.

## 3. Context features (computed by the caller)

Notation: *S* = sender account, *R* = receiver account, *t* = the transaction being scored, *H(S, w)* = set of S's transactions earlier than t inside window w, *I(R, w)* = set of transactions earlier than t that paid R inside window w.

| Feature | Definition | Type | Null? |
|---|---|---|---|
| `sender_txn_count_1h` | `|H(S, 1h)|` | int >= 0 | never |
| `sender_txn_count_24h` | `|H(S, 24h)|` | int >= 0 | never |
| `sender_amount_sum_24h` | sum of `amount` over H(S, 24h); 0 if empty | float >= 0 | never |
| `sender_unique_receivers_24h` | number of distinct receivers over H(S, 24h) | int >= 0 | never |
| `sender_avg_amount_30d` | mean of `amount` over H(S, 30d) | float >= 0 | null if H(S, 30d) is empty |
| `is_new_receiver` | no transaction in H(S, 30d) has receiver R | bool | never |
| `receiver_incoming_count_24h` | `|I(R, 24h)|` | int >= 0 | never |
| `receiver_unique_senders_24h` | number of distinct senders over I(R, 24h) | int >= 0 | never |

All transaction **types** count toward history (a PAYMENT by S counts in S's velocity), but only TRANSFER and CASH_OUT rows are scored and used as training examples. This matters: **history is computed on the full log before filtering to the modelled types.** In the training pipeline, compute context features first, then filter.

## 4. Per-request features (computed inside the ML service)

| Feature | Definition |
|---|---|
| `amount` | as received |
| `amount_log` | `log1p(amount)` |
| `hour_of_day` | hour (0 to 23) of `timestamp`; in training, `(step - 1) mod 24` |
| `day_of_week` | 0 to 6 from `timestamp`; in training, `((step - 1) // 24) mod 7` (synthetic, documented as such) |
| `is_cash_out` | 1 if `type == CASH_OUT`, else 0 (TRANSFER = 0) |
| `amount_to_avg_ratio` | `amount / sender_avg_amount_30d`; null if that is null or 0 |
| `sender_amount_sum_24h_ratio` | `amount / (sender_amount_sum_24h + amount)` |
| `receiver_fan_in_ratio` | `receiver_unique_senders_24h / max(receiver_incoming_count_24h, 1)` |

Missing-value policy: nulls are passed to LightGBM as missing (it handles them natively). For the logistic-regression baseline, impute with the training median and add an `is_missing` indicator.

## 5. Model input (v1 feature list)

Order matters and is stored with the model.

```
amount, amount_log, hour_of_day, day_of_week, is_cash_out,
sender_txn_count_1h, sender_txn_count_24h, sender_amount_sum_24h,
sender_unique_receivers_24h, sender_avg_amount_30d, is_new_receiver,
receiver_incoming_count_24h, receiver_unique_senders_24h,
amount_to_avg_ratio, sender_amount_sum_24h_ratio, receiver_fan_in_ratio
```

Account IDs, `txn_id`, balances, `currency`, `channel`, and `metadata` are **not** model inputs.

## 6. Reason codes (v1: rule-based on the features)

Computed after scoring, only when `decision` is REVIEW or BLOCK, from the table below. Return at most 5, ordered by the listed priority.

| Priority | Code | Condition (initial values; tune against validation data) |
|---|---|---|
| 1 | `HIGH_AMOUNT` | `amount` at or above the training-set 99th percentile of fraud-eligible types |
| 2 | `NEW_RECEIVER` | `is_new_receiver` is true |
| 3 | `HIGH_SENDER_VELOCITY` | `sender_txn_count_1h` at or above the 99th percentile |
| 4 | `HIGH_SENDER_AMOUNT_24H` | `sender_amount_sum_24h` at or above the 99th percentile |
| 5 | `UNUSUAL_AMOUNT_FOR_SENDER` | `amount_to_avg_ratio` at or above 10 |
| 6 | `RECEIVER_FAN_IN` | `receiver_unique_senders_24h` at or above the 99th percentile |
| 7 | `RISKY_TRANSACTION_TYPE` | type is CASH_OUT |
| n/a | `UNSCORED_TYPE` | returned alone when `scored_by_model=false` |

The percentile cut-offs are computed on the training split and stored in `metadata.json`. (A later version may replace this with SHAP-based explanations; that would be a contract 1.1 change if it adds fields.)

## 7. Parity requirements (training-serving consistency)

Required checks (see testing strategy):

1. **Unit tests** for every context feature using tiny hand-made transaction logs, including edge cases: first-ever transaction, two transactions in the same bucket, a transaction exactly 24 buckets ago (excluded) versus 23 buckets ago (included), identical timestamps.
2. **Parity test:** replay a sample of at least 50,000 rows in event order through the reference streaming implementation (`app/features/context.py`, used by `scripts/replay_stream.py`) and compare every context feature against the offline training table. Zero mismatches allowed.
3. **Java conformance (later):** the same replay sample is exported as a JSON fixture; the Java service's tests must reproduce the context values from it.

## 8. Open questions to resolve during EDA

| Question | Decide by |
|---|---|
| Are the two receiver features adding value? (If not, drop them before freezing the contract) | End of Phase 2 |
| Is `day_of_week` meaningful for a synthetic 31-day log? (Likely drop) | End of Phase 2 |
| Are the 99th-percentile cut-offs sensible for reason codes? | Phase 4 |
| Does PaySim contain rows with `amount` = 0? (The contract requires `amount` > 0, so such rows could never arrive in production. If they exist, check how many are fraud, then drop them from training and record that in the model card. Not verified yet.) | Phase 1 EDA |

> Any feature added or removed after the contract is frozen is a contract change (see `contracts/README.md`).
