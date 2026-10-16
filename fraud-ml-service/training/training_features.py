"""
Step 2: Build context features (velocity, history) + per-row features.
All history is computed on the full log (all types), then we filter to TRANSFER/CASH_OUT.
Run from fraud-ml-service/: python training/build_features.py
"""
import yaml
import pandas as pd
import numpy as np
from pathlib import Path

config_path = Path(__file__).parent.parent / "config" / "training.yaml"
with open(config_path) as f:
    cfg = yaml.safe_load(f)

project_root = Path(__file__).resolve().parent.parent
processed_dir = project_root / cfg["dataset"]["processed_dir"]
paysim = pd.read_parquet(processed_dir / "paysim_clean.parquet")
paysim = paysim.reset_index()  # bring event_idx from index into a regular column
print(f"Loaded {len(paysim):,} rows")

# Sort by (step, event_idx) — this IS the event order
paysim = paysim.sort_values(["step", "event_idx"]).reset_index(drop=True)

# ─── Context features (computed on ALL rows, all types) ───────────────────────
# Strategy: for each sender, compute cumulative aggregates per step-bucket,
# then look back over 1h (1 bucket), 24h (24 buckets), 30d (720 buckets).

print("Building per-sender per-step aggregates ...")

# Step 1: aggregate amounts and counts per (sender, step)
sender_step = (
    paysim
    .groupby(["nameOrig", "step"], observed=True)["amount"]
    .agg(["count", "sum"])
    .rename(columns={"count": "txn_count", "sum": "amount_sum"})
    .reset_index()
)

# unique receivers per (sender, step)
sender_step_recv = (
    paysim
    .groupby(["nameOrig", "step"], observed=True)["nameDest"]
    .nunique()
    .rename("unique_receivers")
    .reset_index()
)

sender_step = sender_step.merge(sender_step_recv, on=["nameOrig", "step"], how="left")

print("Building rolling windows per sender ...")

def rolling_window_features(group, windows):
    """For a single sender, build cumulative windows (EXCLUDING current step's self)."""
    group = group.sort_values("step").set_index("step")
    result = {}
    for w_name, w_size in windows.items():
        # Rolling sum over w_size buckets, then subtract current step's own contribution
        # so current step is NOT included
        rolled_count = group["txn_count"].rolling(window=w_size, min_periods=1).sum()
        rolled_sum = group["amount_sum"].rolling(window=w_size, min_periods=1).sum()
        rolled_recv = group["unique_receivers"].rolling(window=w_size, min_periods=1).sum()
        result[f"count_{w_name}"] = rolled_count.shift(1).fillna(0)
        result[f"sum_{w_name}"] = rolled_sum.shift(1).fillna(0)
        result[f"recv_{w_name}"] = rolled_recv.shift(1).fillna(0)
    return pd.DataFrame(result, index=group.index).reset_index()

windows = {
    "1h": cfg["windows_in_hour_buckets"]["w1h"],
    "24h": cfg["windows_in_hour_buckets"]["w24h"],
    "30d": cfg["windows_in_hour_buckets"]["w30d"],
}

# For speed: process per sender using groupby apply
sender_features = (
    sender_step
    .groupby("nameOrig", observed=True, group_keys=True)
    .apply(lambda g: rolling_window_features(g, windows), include_groups=False)
    .reset_index()
)
# sender_features now has columns: ['nameOrig', 'level_1', 'step', 'count_1h', 'sum_1h', 'recv_1h', 'count_24h', 'sum_24h', 'recv_24h', 'count_30d', 'sum_30d', 'recv_30d']
# Rename to match the feature contract and schema
sender_features = sender_features.rename(columns={
    "count_1h": "sender_txn_count_1h",
    "count_24h": "sender_txn_count_24h",
    "sum_24h": "sender_amount_sum_24h",
    "recv_24h": "sender_unique_receivers_24h",
})

# Now join back to the main dataset
print("Joining sender features to main dataset ...")
paysim_feat = paysim.merge(
    sender_features[["nameOrig", "step", "sender_txn_count_1h", "sender_txn_count_24h", "sender_amount_sum_24h", "sender_unique_receivers_24h", "count_30d", "sum_30d"]],
    on=["nameOrig", "step"],
    how="left",
)
paysim_feat["sender_txn_count_1h"] = paysim_feat["sender_txn_count_1h"].fillna(0).astype(int)
paysim_feat["sender_txn_count_24h"] = paysim_feat["sender_txn_count_24h"].fillna(0).astype(int)
paysim_feat["sender_amount_sum_24h"] = paysim_feat["sender_amount_sum_24h"].fillna(0.0)
paysim_feat["sender_unique_receivers_24h"] = paysim_feat["sender_unique_receivers_24h"].fillna(0).astype(int)

# sender_avg_amount_30d (null if no history)
paysim_feat["sender_avg_amount_30d"] = np.where(
    paysim_feat["count_30d"] > 0,
    paysim_feat["sum_30d"] / paysim_feat["count_30d"],
    np.nan
)

# is_new_receiver: has sender ever paid this receiver in the 30d window BEFORE this event?
# Vectorized approach: for each (sender, receiver) pair sorted by (step, event_idx),
# the FIRST occurrence is always "new". For subsequent occurrences, check if the
# previous occurrence of the same pair falls within the 30d window.
print("Computing is_new_receiver (vectorized) ...")
paysim_sorted = paysim.sort_values(["step", "event_idx"]).reset_index(drop=True)

# For each (sender, receiver) pair, find the step of the previous encounter
pair_df = paysim_sorted[["nameOrig", "nameDest", "step"]].copy()
pair_df["_orig_idx"] = paysim_sorted.index

# Within each (sender, receiver) group, shift the step to get "previous encounter step"
pair_df["_prev_step"] = (
    pair_df.groupby(["nameOrig", "nameDest"], observed=True)["step"]
    .shift(1)  # NaN for first encounter; previous step otherwise
)

# is_new_receiver = True if no previous encounter, OR previous encounter was > 30d ago
w30d = windows["30d"]
is_new_receiver_series = (
    pair_df["_prev_step"].isna() |
    (pair_df["step"] - pair_df["_prev_step"] > w30d)
)

# Align back to paysim_feat index via the original nameOrig/nameDest/step join
paysim_sorted["is_new_receiver"] = is_new_receiver_series.values
# Merge back using the sorted index
paysim_feat = paysim_feat.merge(
    paysim_sorted[["nameOrig", "nameDest", "step", "event_idx", "is_new_receiver"]],
    on=["nameOrig", "nameDest", "step", "event_idx"],
    how="left",
)
paysim_feat["is_new_receiver"] = paysim_feat["is_new_receiver"].fillna(True)
print(f"  is_new_receiver: {paysim_feat['is_new_receiver'].sum():,} new out of {len(paysim_feat):,}")

# ─── Receiver features ────────────────────────────────────────────────────────
print("Building receiver features ...")
receiver_step = (
    paysim
    .groupby(["nameDest", "step"], observed=True)
    .agg(incoming_count=("amount", "count"), unique_senders=("nameOrig", "nunique"))
    .reset_index()
)

def rolling_recv_features(group):
    group = group.sort_values("step").set_index("step")
    return pd.DataFrame({
        "receiver_incoming_count_24h": group["incoming_count"].rolling(24, min_periods=1).sum().shift(1).fillna(0),
        "receiver_unique_senders_24h": group["unique_senders"].rolling(24, min_periods=1).sum().shift(1).fillna(0),
    }, index=group.index).reset_index()

recv_features = (
    receiver_step
    .groupby("nameDest", observed=True, group_keys=True)
    .apply(rolling_recv_features, include_groups=False)
    .reset_index()
)

paysim_feat = paysim_feat.merge(
    recv_features[["nameDest", "step", "receiver_incoming_count_24h", "receiver_unique_senders_24h"]],
    on=["nameDest", "step"],
    how="left",
)
paysim_feat["receiver_incoming_count_24h"] = paysim_feat["receiver_incoming_count_24h"].fillna(0).astype(int)
paysim_feat["receiver_unique_senders_24h"] = paysim_feat["receiver_unique_senders_24h"].fillna(0).astype(int)

# ─── Per-request features (computed inside the ML service too) ───────────────
paysim_feat["amount_log"] = np.log1p(paysim_feat["amount"])
paysim_feat["hour_of_day"] = ((paysim_feat["step"] - 1) % 24).astype(int)
paysim_feat["day_of_week"] = (((paysim_feat["step"] - 1) // 24) % 7).astype(int)
paysim_feat["is_cash_out"] = (paysim_feat["type"] == "CASH_OUT").astype(int)

# Derived features
paysim_feat["amount_to_avg_ratio"] = np.where(
    paysim_feat["sender_avg_amount_30d"].notna() & (paysim_feat["sender_avg_amount_30d"] > 0),
    paysim_feat["amount"] / paysim_feat["sender_avg_amount_30d"],
    np.nan
)
paysim_feat["sender_amount_sum_24h_ratio"] = (
    paysim_feat["amount"] / (paysim_feat["sender_amount_sum_24h"] + paysim_feat["amount"])
)
paysim_feat["receiver_fan_in_ratio"] = (
    paysim_feat["receiver_unique_senders_24h"] / paysim_feat["receiver_incoming_count_24h"].clip(lower=1)
)

# ─── Filter to scored types and assign split ─────────────────────────────────
scored = paysim_feat[paysim_feat["type"].isin(cfg["scored_types"])].copy()
print(f"Filtered to {cfg['scored_types']}: {len(scored):,} rows")

split_cfg = cfg["split"]
def get_split(step):
    if step <= split_cfg["train_steps"][1]:
        return "train"
    elif step <= split_cfg["validation_steps"][1]:
        return "val"
    else:
        return "test"

scored["split"] = scored["step"].map(get_split)
print(f"\nSplit counts:\n{scored.groupby('split')['isFraud'].agg(['count', 'sum'])}")

# Final feature list (from config)
feature_cols = cfg["features"]
label_col = cfg["columns"]["label"]
keep_cols = feature_cols + [label_col, "step", "split", "nameOrig", "nameDest"]

output = scored[[c for c in keep_cols if c in scored.columns]].copy()
output_path = processed_dir / "features.parquet"
output.to_parquet(output_path, index=False)
print(f"\n✅ Saved features.parquet: {output_path} ({len(output):,} rows)")
print(f"   Columns: {output.columns.tolist()}")
print(f"   Null counts:\n{output[feature_cols].isnull().sum()}")
