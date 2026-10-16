"""
Train the fraud detection model.
Usage:
  python training/train.py --model baseline
  python training/train.py --model lightgbm
  python training/train.py --model lightgbm --search   (hyperparameter search)
"""
import argparse
import json
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    average_precision_score, precision_recall_curve,
    confusion_matrix, classification_report
)
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
import lightgbm as lgb
import joblib

config_path = Path(__file__).parent.parent / "config" / "training.yaml"
with open(config_path) as f:
    cfg = yaml.safe_load(f)

SEED = cfg["seed"]
FEATURES = cfg["features"]
LABEL = cfg["columns"]["label"]
project_root = Path(__file__).resolve().parent.parent
processed_dir = project_root / cfg["dataset"]["processed_dir"]

def load_splits():
    df = pd.read_parquet(processed_dir / "features.parquet")
    train = df[df["split"] == "train"]
    val = df[df["split"] == "val"]
    test = df[df["split"] == "test"]
    print(f"Train: {len(train):,} rows, {train[LABEL].sum()} fraud")
    print(f"Val:   {len(val):,} rows, {val[LABEL].sum()} fraud")
    print(f"Test:  {len(test):,} rows, {test[LABEL].sum()} fraud")
    return train, val, test

def evaluate(name, y_true, y_pred_proba, thresholds=None):
    pr_auc = average_precision_score(y_true, y_pred_proba)
    print(f"\n--- {name} ---")
    print(f"PR-AUC: {pr_auc:.4f}")
    
    precision, recall, thresh = precision_recall_curve(y_true, y_pred_proba)
    
    # Recall at precision >= 0.90
    mask = precision >= 0.90
    if mask.any():
        r_at_p90 = recall[mask].max()
        print(f"Recall @ Precision>=0.90: {r_at_p90:.4f}")
    
    # Recall at precision >= 0.50
    mask = precision >= 0.50
    if mask.any():
        r_at_p50 = recall[mask].max()
        print(f"Recall @ Precision>=0.50: {r_at_p50:.4f}")
    
    if thresholds:
        for tname, t in thresholds.items():
            y_pred = (y_pred_proba >= t).astype(int)
            cm = confusion_matrix(y_true, y_pred)
            print(f"\nThreshold {tname}={t:.3f}:")
            print(f"  TP={cm[1,1]}, FP={cm[0,1]}, TN={cm[0,0]}, FN={cm[1,0]}")
            print(f"  Precision={cm[1,1]/(cm[1,1]+cm[0,1]+1e-9):.4f}, Recall={cm[1,1]/(cm[1,1]+cm[1,0]+1e-9):.4f}")
    
    return {"pr_auc": pr_auc}

def choose_thresholds(y_val, val_proba, cfg_thresh):
    """Select block and review thresholds from validation set."""
    precision, recall, thresholds = precision_recall_curve(y_val, val_proba)
    
    # Block threshold: highest recall s.t. precision >= 0.90
    min_prec = cfg_thresh["block"]["min_precision"]
    mask = precision[:-1] >= min_prec
    if mask.any():
        best_idx = recall[:-1][mask].argmax()
        block_thresh = thresholds[np.where(mask)[0][best_idx]]
    else:
        block_thresh = 0.9  # fallback
    
    # Review threshold: at most 1% review volume
    # review = score >= review_thresh and score < block_thresh
    max_vol = cfg_thresh["review"]["max_review_volume"]
    for t in sorted(thresholds, reverse=True):
        review_vol = ((val_proba >= t) & (val_proba < block_thresh)).mean()
        if review_vol <= max_vol:
            review_thresh = t
            break
    else:
        review_thresh = block_thresh - 0.05
    
    return {"block": float(block_thresh), "review": float(review_thresh)}

def train_baseline(train, val):
    print("\n=== Training Logistic Regression Baseline ===")
    X_train = train[FEATURES]
    y_train = train[LABEL]
    X_val = val[FEATURES]
    y_val = val[LABEL]
    
    pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            class_weight="balanced",
            max_iter=cfg["baselines"]["logistic_regression"]["max_iter"],
            random_state=SEED,
        ))
    ])
    pipe.fit(X_train, y_train)
    val_proba = pipe.predict_proba(X_val)[:, 1]
    metrics = evaluate("Logistic Regression (Val)", y_val, val_proba)
    
    # Trivial rule baseline
    pct99 = train[FEATURES[0]].quantile(0.99)  # amount 99th pct
    trivial_score = (train[FEATURES[0]] >= pct99).astype(float)
    trivial_val = (val[FEATURES[0]] >= pct99).astype(float)
    trivial_metrics = evaluate("Trivial Rule (Val, amount>=99pct)", y_val, trivial_val)
    print(f"\nTrivial rule 99th pct amount cutoff: {pct99:,.2f}")
    
    return pipe, metrics

def train_lightgbm(train, val, search=False):
    print("\n=== Training LightGBM ===")
    X_train = train[FEATURES].values
    y_train = train[LABEL].values
    X_val = val[FEATURES].values
    y_val = val[LABEL].values
    
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale_pos_weight = neg / pos
    print(f"scale_pos_weight: {scale_pos_weight:.1f} (neg={neg:,}, pos={pos:,})")
    
    params = dict(cfg["lightgbm"]["params"])
    params["scale_pos_weight"] = scale_pos_weight
    params["random_state"] = SEED
    params["verbose"] = -1
    
    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(cfg["lightgbm"]["early_stopping_rounds"], verbose=True),
            lgb.log_evaluation(100),
        ],
    )
    
    val_proba = model.predict_proba(X_val)[:, 1]
    metrics = evaluate("LightGBM (Val)", y_val, val_proba)
    
    thresholds = choose_thresholds(y_val, val_proba, cfg["thresholds"])
    print(f"\nChosen thresholds: {thresholds}")
    
    return model, metrics, thresholds, val_proba, y_val

def export_model(model, metrics, thresholds, test_metrics, val_data, test_data, model_type="lightgbm"):
    import hashlib, datetime, subprocess, platform
    
    export_dir = project_root / cfg["export"]["model_dir"]
    # Find next version
    existing = sorted([d.name for d in export_dir.iterdir() if d.is_dir() and d.name.startswith("v")])
    next_v = f"v{len(existing) + 1}"
    model_dir = export_dir / next_v
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Save model
    joblib.dump(model, model_dir / "model.joblib")
    
    # Feature list
    import json
    (model_dir / "feature_list.json").write_text(json.dumps(FEATURES))
    
    # Thresholds
    import yaml as _yaml
    (model_dir / "thresholds.yaml").write_text(_yaml.dump(thresholds))
    
    # Metrics
    (model_dir / "metrics.json").write_text(json.dumps({
        "val": metrics, "test": test_metrics
    }, indent=2))
    
    # Metadata
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    except Exception:
        git_commit = "unknown"
    
    meta = {
        "model_version": next_v,
        "model_type": model_type,
        "trained_at": datetime.datetime.utcnow().isoformat() + "Z",
        "dataset": {"name": cfg["dataset"]["name"], "source": cfg["dataset"]["source"]},
        "split_boundaries": cfg["split"],
        "feature_list": FEATURES,
        "feature_list_hash": hashlib.md5(json.dumps(FEATURES).encode()).hexdigest(),
        "random_seed": SEED,
        "library_versions": {
            "python": platform.python_version(),
            "lightgbm": lgb.__version__,
            "sklearn": __import__("sklearn").__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "git_commit": git_commit,
    }
    (model_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    
    # Promote CURRENT
    (export_dir / "CURRENT").write_text(next_v)
    
    print(f"\n✅ Model exported to {model_dir}")
    print(f"   CURRENT -> {next_v}")
    return next_v

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["baseline", "lightgbm"], default="lightgbm")
    parser.add_argument("--search", action="store_true", help="Run hyperparameter search")
    parser.add_argument("--export", action="store_true", help="Export artifacts after training")
    args = parser.parse_args()
    
    train, val, test = load_splits()
    
    if args.model == "baseline":
        model, metrics = train_baseline(train, val)
    else:
        model, metrics, thresholds, val_proba, y_val = train_lightgbm(train, val, args.search)
        
        # Final test evaluation (run once!)
        X_test = test[FEATURES].values
        y_test = test[LABEL].values
        test_proba = model.predict_proba(X_test)[:, 1]
        test_metrics = evaluate("LightGBM (Test)", y_test, test_proba, thresholds)
        
        if args.export:
            version = export_model(model, metrics, thresholds, test_metrics, val, test)
