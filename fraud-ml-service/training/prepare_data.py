"""
Step 1: Load PaySim CSV, apply dtypes, add event order index, save as Parquet.
Run from fraud-ml-service/: python training/prepare_data.py
"""
import yaml
import pandas as pd
from pathlib import Path

# Load config
config_path = Path(__file__).parent.parent / "config" / "training.yaml"
with open(config_path) as f:
    cfg = yaml.safe_load(f)

# Resolve paths relative to fraud-ml-service root
project_root = Path(__file__).resolve().parent.parent
raw_path = project_root / cfg["dataset"]["raw_path"]
out_dir = project_root / cfg["dataset"]["processed_dir"]
out_dir.mkdir(parents=True, exist_ok=True)

print(f"Loading {raw_path} ...")
dtypes = {
    "step": "int16",
    "type": "category",
    "amount": "float32",
    "nameOrig": "str",
    "nameDest": "str",
    "isFraud": "int8",
    "isFlaggedFraud": "int8",
    # Balance columns — load but will drop
    "oldbalanceOrg": "float32",
    "newbalanceOrig": "float32",
    "oldbalanceDest": "float32",
    "newbalanceDest": "float32",
}

df = pd.read_csv(raw_path, dtype=dtypes)
print(f"  Loaded: {len(df):,} rows")

# Drop excluded columns (ADR-0005)
excluded = cfg["columns"]["excluded"]
df = df.drop(columns=[c for c in excluded if c in df.columns])
print(f"  Dropped excluded columns: {excluded}")

# Handle rows with amount <= 0 (PaySim has 16 zero-amount rows)
# The contract enforces amount > 0, so zero amounts cannot occur in production.
zero_amt_mask = df["amount"] <= 0
num_zero = zero_amt_mask.sum()
if num_zero > 0:
    zero_fraud = df.loc[zero_amt_mask, "isFraud"].sum()
    print(f"  Filtering {num_zero} rows with amount <= 0 ({zero_fraud} were fraud)")
    df = df[~zero_amt_mask].copy()

# Add event order index (sort key for point-in-time correctness)
df = df.reset_index(drop=True)
df.index.name = "event_idx"

# Verify no nulls and positive amounts
assert df["step"].notna().all(), "step has nulls"
assert df["amount"].notna().all(), "amount has nulls"
assert (df["amount"] > 0).all(), "Found remaining zero/negative amounts"

out_path = out_dir / "paysim_clean.parquet"
df.to_parquet(out_path, index=True)
print(f"  Saved: {out_path}  ({len(df):,} rows)")

# Quick sanity stats
print(f"\n  Types: {df['type'].value_counts().to_dict()}")
print(f"  Fraud rate: {df['isFraud'].mean()*100:.3f}%")
print(f"  Step range: {df['step'].min()} to {df['step'].max()}")
print("✅ Done: prepare_data.py")
