"""
Tests for the Compound-Risk XGBoost Scorer.

Run with: python -m pytest backend/app/ml/scoring/tests/test_scoring.py -v
Requires a trained model.pkl -- run `python -m backend.app.ml.scoring.train`
first if this is a fresh checkout (model.pkl is a build artifact, not
guaranteed to be committed).
"""

import pytest

from ..train import generate_dataset, train_model, FEATURE_COLUMNS
from ..infer import CompoundRiskScorer
from ...anomaly.isolation_forest import ZoneSensorAnomalyDetector  # noqa: F401 (import sanity check)
from ....workers.features import RollingFeatureStore, compute_window_stats


def test_generate_dataset_has_expected_shape_and_balance():
    df = generate_dataset(n_samples=500, positive_fraction=0.3, seed=1)
    assert len(df) == 500
    assert set(FEATURE_COLUMNS + ["label"]) == set(df.columns)
    assert df["label"].sum() == pytest.approx(150, abs=5)  # ~30% positive


def test_train_model_beats_a_coin_flip_by_a_wide_margin():
    df = generate_dataset(n_samples=1500, positive_fraction=0.3, seed=2)
    model, metrics = train_model(df, seed=2)
    assert metrics["val_precision"] > 0.9
    assert metrics["val_recall"] > 0.9
    assert metrics["val_auc"] > 0.95


def test_infer_wrapper_returns_0_to_100_range():
    scorer = pytest.importorskip("backend.app.ml.scoring.infer")
    from ..infer import CompoundRiskScorer
    try:
        s = CompoundRiskScorer()
    except FileNotFoundError:
        pytest.skip("model.pkl not built yet -- run train.py first")

    low_risk = {
        "gas_trend_slope": 0.0, "permit_zone_overlap_count": 0,
        "shift_boundary_proximity_s": 5000, "equipment_maintenance_overdue_flag": 0,
        "cv_occupancy_count": 1, "historical_incident_similarity_score": 0.05,
    }
    high_risk = {
        "gas_trend_slope": 0.015, "permit_zone_overlap_count": 1,
        "shift_boundary_proximity_s": 300, "equipment_maintenance_overdue_flag": 1,
        "cv_occupancy_count": 3, "historical_incident_similarity_score": 0.8,
    }
    low_score = s.score(low_risk)
    high_score = s.score(high_risk)
    assert 0 <= low_score <= 100
    assert 0 <= high_score <= 100
    assert high_score > low_score


def test_infer_wrapper_degrades_gracefully_on_missing_features():
    try:
        s = CompoundRiskScorer()
    except FileNotFoundError:
        pytest.skip("model.pkl not built yet -- run train.py first")
    # only partial features supplied -- should not raise
    score = s.score({"gas_trend_slope": 0.01})
    assert 0 <= score <= 100


# ---------------------------------------------------------------------------
# Regression test for the fill-fraction bug: a slope computed from a window
# that's barely started filling must be suppressed (0.0), not amplified into
# a spurious value that would trip the scorer on pure sensor noise.
# ---------------------------------------------------------------------------

def test_partial_window_slope_is_suppressed_until_mostly_full():
    times = [0, 20, 40]  # only 40s of a 300s window -- noisy, should be suppressed
    values = [8.0, 9.5, 7.2]  # noisy, no real trend
    stats = compute_window_stats(times, values, window_s=300)
    assert stats["trend_slope_per_s"] == 0.0


def test_full_window_slope_is_trusted():
    times = list(range(0, 301, 30))  # spans the full 300s window
    values = [8.0 + 0.01 * t for t in times]  # clean linear drift
    stats = compute_window_stats(times, values, window_s=300)
    assert stats["trend_slope_per_s"] == pytest.approx(0.01, abs=1e-6)
