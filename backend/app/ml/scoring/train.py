"""
Compound-Risk XGBoost Scorer -- feature engineering + training.

Feature vector (matches what CompoundRiskAgent already assembles for the
scorer slot in compound_risk_agent.py, plus two features pending other
modules -- see notes below):
    gas_trend_slope              ppm/s, 5-min rolling window
    permit_zone_overlap_count    # active permits in the zone (hot-work-weighted)
    shift_boundary_proximity_s   seconds until next shift boundary
    equipment_maintenance_overdue_flag   0/1 -- PLACEHOLDER: no maintenance
                                  system exists yet; synthesized here so the
                                  schema is ready. Wire to the real signal
                                  once it exists; until then this column is
                                  effectively noise the model should learn
                                  to weight near-zero on its own.
    cv_occupancy_count           from Module 4's ZoneOccupancyCounter
    historical_incident_similarity_score  0-1 -- PLACEHOLDER pending
                                  Member 3's RAG output; synthesized here too.

Training data is generated synthetically (with parameter jitter) rather
than by running the full simulator end-to-end, so a full labeled dataset
can be produced in seconds without spinning up Redis/Neo4j. The synthetic
ground-truth rule intentionally includes a second risk pathway (maintenance
+ occupancy + gas trend) that CompoundRiskAgent's hand-written 3-condition
rule does NOT check -- this is what the model needs to learn to genuinely
beat the rule-only baseline, not just re-derive it.
"""

import pickle
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

FEATURE_COLUMNS = [
    "gas_trend_slope",
    "permit_zone_overlap_count",
    "shift_boundary_proximity_s",
    "equipment_maintenance_overdue_flag",
    "cv_occupancy_count",
    "historical_incident_similarity_score",
]

MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"
GAS_TREND_NOISE_FLOOR = 0.001  # ppm/s -- below this is indistinguishable from sensor noise


def _sample_negative(rng: np.random.Generator) -> dict:
    """A 'safe' moment: at most one weak risk factor present, nothing corroborating."""
    return {
        "gas_trend_slope": max(0.0, rng.normal(0.0, 0.0015)),
        "permit_zone_overlap_count": rng.choice([0, 0, 0, 1], p=[0.6, 0.2, 0.15, 0.05]),
        "shift_boundary_proximity_s": rng.uniform(1800, 6 * 3600),  # outside the 30-min window
        "equipment_maintenance_overdue_flag": rng.choice([0, 1], p=[0.92, 0.08]),
        "cv_occupancy_count": rng.poisson(1.5),
        "historical_incident_similarity_score": rng.beta(1.5, 6),  # skewed low
    }


def _sample_positive_permit_pathway(rng: np.random.Generator) -> dict:
    """Mirrors compound_risk_scenario_1.py: permit + gas drift + shift boundary overlap."""
    return {
        "gas_trend_slope": rng.uniform(0.004, 0.02),
        "permit_zone_overlap_count": rng.choice([1, 2], p=[0.8, 0.2]),
        "shift_boundary_proximity_s": rng.uniform(0, 1800),
        "equipment_maintenance_overdue_flag": rng.choice([0, 1], p=[0.7, 0.3]),
        "cv_occupancy_count": rng.poisson(2.5),
        "historical_incident_similarity_score": rng.beta(3, 3),
    }


def _sample_positive_maintenance_pathway(rng: np.random.Generator) -> dict:
    """
    Second, rule-agent-blind risk pathway: overdue maintenance + elevated
    occupancy + rising gas trend, WITHOUT necessarily having a hot-work
    permit or an imminent shift boundary. CompoundRiskAgent's 3-condition
    rule would miss this; the scorer shouldn't.
    """
    return {
        "gas_trend_slope": rng.uniform(0.003, 0.015),
        "permit_zone_overlap_count": rng.choice([0, 1], p=[0.6, 0.4]),
        "shift_boundary_proximity_s": rng.uniform(1800, 6 * 3600),
        "equipment_maintenance_overdue_flag": 1,
        "cv_occupancy_count": rng.poisson(4),  # more people around = more exposure
        "historical_incident_similarity_score": rng.beta(4, 2),  # skewed high
    }


def generate_dataset(n_samples: int = 4000, positive_fraction: float = 0.3,
                      seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_positive = int(n_samples * positive_fraction)
    n_negative = n_samples - n_positive
    n_pos_permit = n_positive // 2
    n_pos_maint = n_positive - n_pos_permit

    rows = []
    for _ in range(n_negative):
        row = _sample_negative(rng)
        row["label"] = 0
        rows.append(row)
    for _ in range(n_pos_permit):
        row = _sample_positive_permit_pathway(rng)
        row["label"] = 1
        rows.append(row)
    for _ in range(n_pos_maint):
        row = _sample_positive_maintenance_pathway(rng)
        row["label"] = 1
        rows.append(row)

    df = pd.DataFrame(rows)
    return df.sample(frac=1.0, random_state=seed).reset_index(drop=True)  # shuffle


def train_model(df: pd.DataFrame, seed: int = 42) -> Tuple[XGBClassifier, dict]:
    X = df[FEATURE_COLUMNS]
    y = df["label"]
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    model = XGBClassifier(
        n_estimators=150, max_depth=4, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric="logloss", random_state=seed,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    val_preds = model.predict(X_val)
    val_probs = model.predict_proba(X_val)[:, 1]
    from sklearn.metrics import precision_score, recall_score, roc_auc_score
    metrics = {
        "val_precision": precision_score(y_val, val_preds),
        "val_recall": recall_score(y_val, val_preds),
        "val_auc": roc_auc_score(y_val, val_probs),
        "feature_importances": dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist())),
    }
    return model, metrics


def save_model(model: XGBClassifier, path: Path = MODEL_PATH):
    with open(path, "wb") as f:
        pickle.dump({"model": model, "feature_columns": FEATURE_COLUMNS}, f)


def main():
    print("Generating labeled training data...")
    df = generate_dataset(n_samples=4000, positive_fraction=0.3, seed=42)
    print(f"  {len(df)} samples ({df['label'].sum()} positive, {len(df) - df['label'].sum()} negative)")

    print("Training XGBoost classifier...")
    model, metrics = train_model(df, seed=42)

    print(f"  Validation precision: {metrics['val_precision']:.3f}")
    print(f"  Validation recall:    {metrics['val_recall']:.3f}")
    print(f"  Validation AUC:       {metrics['val_auc']:.3f}")
    print("  Feature importances (for the pitch/demo narrative):")
    for feat, imp in sorted(metrics["feature_importances"].items(), key=lambda x: -x[1]):
        print(f"    {feat:38s} {imp:.3f}")

    save_model(model)
    print(f"\nModel saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
