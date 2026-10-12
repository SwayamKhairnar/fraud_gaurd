# 04. Conventions

Small, boring rules that keep a multi-service project consistent.

## 1. Naming

| Thing | Convention | Example |
|---|---|---|
| Services / repos folders | kebab-case | `fraud-ml-service` |
| Python modules and functions | snake_case | `build_features()` |
| Python classes | PascalCase | `PredictRequest` |
| JSON fields (contracts) | snake_case | `sender_txn_count_24h` |
| Kafka topics | dot.separated lowercase | `fraud.decisions` |
| Env vars | UPPER_SNAKE_CASE | `MODEL_DIR` |
| Docs | numbered prefix + kebab-case | `03-training-plan.md` |
| ADRs | `NNNN-short-title.md` | `0003-dataset-paysim-primary.md` |

## 2. Git

- Branches: `main` is always working. Work on `feature/<short-name>`, `fix/<short-name>`, `docs/<short-name>`.
- Commit messages follow Conventional Commits: `type(scope): summary`.
  - Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.
  - Examples: `feat(ml): add hour-bucket velocity features`, `docs(contracts): clarify is_new_receiver`.
- Small commits. One logical change per commit.
- Tags: `contracts-v1.0`, `fraud-ml-service-v0.1.0`.
- Never commit: raw data, secrets, `.env`, virtual environments, large model binaries.

## 3. Versioning (three independent version numbers)

| Artifact | Scheme | What a bump means |
|---|---|---|
| Contract (`schema_version`) | `MAJOR.MINOR` | MINOR: additive optional fields. MAJOR: any breaking change. Every change needs an ADR or a CHANGELOG entry |
| Model (`model_version`) | `vN` (v1, v2, ...) | New training run promoted to serving. Never overwrite an existing version |
| Service (code) | SemVer `x.y.z` | Normal release versioning |

The response always includes `model_version` so every score can be traced to the exact model that produced it.

## 4. Python code style

- Python 3.11, type hints on all public functions.
- Formatting and linting with Ruff (`ruff check .`, `ruff format .`).
- Keep layers separate:
  - `app/api/`: HTTP only (parsing, status codes). No ML logic.
  - `app/features/`: pure functions, shared by training and serving.
  - `app/model/`: loading, predicting, thresholds, reason codes.
  - `app/core/`: config, logging, metrics, errors.
- Feature code must be **pure** (same inputs give the same outputs, no hidden state, no I/O).

## 5. Configuration

- Config comes from `config/*.yaml` (defaults) overridden by environment variables.
- No secrets in the repo. `.env.example` documents variables; `.env` is local only.
- Thresholds are config, never hard-coded.

## 6. Logging

- JSON logs to stdout, one object per line.
- Mandatory fields: `timestamp`, `level`, `service`, `request_id`, and when relevant `txn_id`, `model_version`, `decision`, `latency_ms`.
- Do not log full account identifiers; log a short hash.

## 7. Errors

- All error responses follow `contracts/error.schema.json`.
- Use `422` for contract violations, `503` when the model is not ready, `500` for unexpected failures.
- Never leak stack traces in responses.

## 8. Testing

- Test files named `test_<module>.py`, test functions `test_<behaviour>`.
- Every bug fix gets a regression test.
- Contract tests validate every file in `contracts/examples/` against its schema.

## 9. Documentation

- Docs live next to the thing they describe.
- Every non-obvious decision gets an ADR (`docs/adr/0000-template.md`).
- A change that affects another service must update the contract docs and the CHANGELOG in the same commit.

## 10. Pull request / self-review checklist

- [ ] Tests added or updated, and passing
- [ ] `ruff check .` clean
- [ ] Contract examples still validate
- [ ] Docs and CHANGELOG updated if behaviour or contract changed
- [ ] No data, secrets, or large binaries committed
