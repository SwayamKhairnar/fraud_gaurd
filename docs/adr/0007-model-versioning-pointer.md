# ADR-0007: Model artifact versioning with a `CURRENT` pointer file

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Swayam

## Context

The service must load a specific model version, report it in every response, and allow a quick rollback. A full model registry (for example MLflow) is more than the project needs.

## Decision

Each trained model lives in its own immutable directory `artifacts/models/vN/`, containing the model file, `feature_list.json`, `metadata.json`, `metrics.json`, and `thresholds.yaml`. A plain text file `artifacts/models/CURRENT` contains the active version name (for example `v1`). The service reads `CURRENT` at startup and loads that directory. Promotion and rollback are done by editing that file and restarting (or reloading) the service.

A plain text pointer is used instead of a symbolic link because symlinks are unreliable on Windows and in some Docker volume setups.

## Consequences

- **Positive:** trivial to understand and operate; fully reproducible; works the same on every OS; rollback is a one-line change.
- **Negative:** no UI, no lineage tracking, no automatic comparison between versions. The model card and `metrics.json` carry that information manually.
- **Follow-ups:** `scripts/` includes a promote helper (later); the service exposes the active version at `/v1/model-info` and in every response.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| MLflow model registry | Extra service and learning curve; revisit if models multiply |
| Single `model.joblib` overwritten on retrain | No rollback, no traceability |
| Symlink `current -> vN` | Windows and volume-mount problems |
