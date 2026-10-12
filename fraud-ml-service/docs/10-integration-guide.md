# 10. Integration Guide (for `fraud-detection-service` and other callers)

How to use the ML service correctly from another service. Written for the Java/Spring Boot fraud-detection-service; the principles apply to any caller. Contract details: `contracts/README.md`. Sections marked **(proposed)** are a design for Phase 9, not yet built.

## 1. The calling pattern

1. Receive a transaction to evaluate.
2. Compute the `context` features from your own state (see section 5).
3. `POST /v1/predict` with the request body from `contracts/predict-request.schema.json`.
4. Combine the response with your rules and decide.
5. **After** deciding, update your state (counters) so the transaction is included in future history, but not in its own context.

## 2. Timeouts, retries, fallbacks

| Topic | Rule |
|---|---|
| Connect timeout | 50 ms |
| Read timeout (total budget) | about 150 ms |
| Retries | At most 1 retry, only on timeout or connection error. Scoring is idempotent, so a retry is safe |
| Circuit breaker | Open after repeated failures or slow calls; stay open for a short period, then probe (half-open) |
| Fallback | Rules-only decision; record `scored_by=RULES` in your decision log |
| 422 | A bug in your payload. Do not retry. Log it and fall back to rules. Treat as an alert |
| 503 `MODEL_NOT_READY` | Treat like an outage; fall back to rules |

Illustrative Spring Boot skeleton (verify annotations and properties against the current Spring and Resilience4j documentation before use):

```java
@CircuitBreaker(name = "fraudMl", fallbackMethod = "rulesOnly")
@Retry(name = "fraudMl")
public MlDecision score(PredictRequest req) {
    return restClient.post()
        .uri("/v1/predict")
        .header("X-Request-ID", MDC.get("requestId"))
        .body(req)
        .retrieve()
        .body(MlDecision.class);
}

private MlDecision rulesOnly(PredictRequest req, Throwable cause) {
    return MlDecision.unscored("RULES");   // scored_by_model = false equivalent
}
```

## 3. Interpreting the response

- Always branch on `scored_by_model` first.
  - `false`: no model opinion; use your own rules. `fraud_score` is null.
  - `true`: `fraud_score` is a number from 0 to 1.
- `decision` is a recommendation. Suggested combination (proposed):

| Rules say | ML says | Final |
|---|---|---|
| BLOCK | anything | BLOCK |
| ALLOW | BLOCK | REVIEW at first (during shadow rollout); BLOCK once trusted |
| ALLOW | REVIEW | REVIEW |
| ALLOW | ALLOW | ALLOW |

- Store `fraud_score`, `decision`, `reason_codes`, and `model_version` with every decision for audit and later retraining.

## 4. Shadow-mode rollout (proposed)

| Stage | Behaviour | Exit condition |
|---|---|---|
| 1. Shadow | Call the ML service, store its output, **ignore it** for decisions | ML output stable for a few days; decision mix understood |
| 2. Advisory | ML can raise ALLOW to REVIEW only | Review quality acceptable |
| 3. Enforced | ML BLOCK is honoured according to the combination table | Ongoing monitoring |

Compare shadow outputs with the rules' decisions on the same traffic to see disagreement rates before trusting the model.

## 5. Computing `context` (proposed reference design)

Definitions are fixed in `docs/02-feature-spec.md` (hour buckets, exclude current, event order). A simple, exact design in Redis:

- For each account keep two sorted sets:
  - `acct:{id}:out`: score = hour bucket, member = `txnId|receiverId|amount`
  - `acct:{id}:in`: score = hour bucket, member = `txnId|senderId|amount`
- To build features for a transaction in bucket `b`:
  1. Trim entries with score below `b - 719` (`ZREMRANGEBYSCORE`) and set a key TTL of 30 days.
  2. Read the sender's `out` set for scores in `[b - 719, b]` (`ZRANGEBYSCORE`); derive the 1h, 24h, and 30d values in application code.
  3. Read the receiver's `in` set for scores in `[b - 23, b]`; derive the receiver features.
- After deciding, add the current transaction to the sender's `out` and the receiver's `in` sets.
- Trade-off: simple and exact, cost grows with an account's activity in 30 days. Acceptable for this project; a counter-based approach is an optimisation, not a necessity.

## 6. Conformance fixtures

- The ML service repository will export a fixture file with a sample of transactions in event order and the expected `context` values (from the reference implementation).
- Your service's tests must reproduce the expected values exactly. This is the safeguard against training-serving skew.

## 7. Using the mock client while the real service is not ready

`scripts/mock_client.py` (to be created in Phase 5) sends realistic requests to the ML service. Other services can also run the ML service container alone and call it directly. No Kafka or Redis is required to develop against it.

## 8. Observability expectations for callers

- Send `X-Request-ID` on every call and log it.
- Record the latency of the call on your side, in addition to the server-side `latency_ms`.
- Expose a metric for fallbacks (for example `fraud_detection_ml_fallback_total{reason}`) and alert on it.

## 9. Checklist before enabling in a caller

- [ ] Payloads validated against `predict-request.schema.json` in tests
- [ ] Context values pass the conformance fixture
- [ ] Timeout, retry, circuit breaker, and fallback tested by killing the ML container
- [ ] Shadow mode enabled first
- [ ] Decisions stored with `model_version`
- [ ] Dashboard shows fallback rate and ML latency
