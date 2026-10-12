# 05. Maintenance

How the project is kept healthy after it is built. Service-specific operations are in `fraud-ml-service/docs/07-runbook.md`.

## 1. Routine checklist

### Weekly (while the project is active)
- [ ] CHANGELOG reflects what changed this week
- [ ] Roadmap checkboxes updated
- [ ] All tests pass on `main`
- [ ] No stale branches

### Monthly (or before showing the project to anyone)
- [ ] Re-install from `requirements.lock` in a fresh venv; tests still pass
- [ ] `docker compose up --build` works from a clean clone
- [ ] Docs match reality (spot-check the quick-start commands)
- [ ] Check dependencies for known security advisories (`pip list --outdated`, `pip-audit` if installed)

## 2. Model maintenance

| Trigger | Action |
|---|---|
| Score distribution drifts (PSI over 0.2 on the monitored window) | Investigate the cause, consider retraining |
| REVIEW + BLOCK rate moves sharply with no known cause | Investigate; compare feature distributions to training |
| New fraud pattern or new transaction type appears | Extend the dataset/features; train a new version |
| Feature definition changes | Retrain, bump `model_version`, update the feature spec and contract if needed |
| Confirmed fraud labels start flowing back (later phase) | Schedule periodic retraining with the labelled data |

Promotion and rollback are done by changing the one-line `artifacts/models/CURRENT` pointer (see the training plan). Old versions are never deleted until a newer version has run cleanly.

## 3. Contract change process

1. Open an ADR (or add a decision to an existing one) describing the change and who is affected.
2. Edit the schema files and examples in `contracts/`.
3. Bump `schema_version` according to `docs/04-conventions.md`.
4. Update the Pydantic models and the feature spec.
5. Run contract tests; they must pass.
6. Update `CHANGELOG.md` with a "Contract" entry.
7. Update every consumer, then every producer, in that order, unless the change is purely additive.

## 4. Dependency policy

- Pin direct dependencies with minimum versions in `requirements*.txt`; keep the exact lock in `requirements.lock`.
- Upgrade deliberately, one group at a time, with tests. Never upgrade LightGBM or scikit-learn without re-running the model tests, because model files can depend on library versions.
- Record the library versions used for training in `metadata.json`.

## 5. Backups and data hygiene

- Model artifacts: keep `metadata.json`, `metrics.json`, `feature_list.json` in Git; keep model binaries in a backup location (cloud drive or release assets) because they are git-ignored.
- Raw datasets: never commit; re-download from the source documented in the dataset plan.
- No real personal data is ever added to the repository.

## 6. Documentation upkeep

- Each ADR is immutable once accepted. To change a decision, write a new ADR that supersedes it and update the old one's status line.
- Keep `docs/02-roadmap.md` honest; it is the first thing a reader looks at.

## 7. Files that exist for maintenance

| File | Purpose |
|---|---|
| `CHANGELOG.md` | Project-level change history |
| `docs/adr/` | Why things are the way they are |
| `docs/05-maintenance.md` | This file |
| `fraud-ml-service/docs/07-runbook.md` | Operating the ML service, incident steps |
| `fraud-ml-service/docs/08-model-card-template.md` | Per-model-version documentation |
| `fraud-ml-service/docs/09-definition-of-done.md` | When the ML service counts as finished |
| `requirements.lock` | Reproducible Python environment |
