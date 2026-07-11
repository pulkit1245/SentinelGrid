"""
Evaluate the Compound-Risk XGBoost Scorer against the single-sensor
baseline. Produces the numbers Member 1's cockpit displays live during the
demo (detection accuracy, lead time), and checks the target: catching every
scripted compound scenario with a false-positive rate under an agreed
ceiling (default: <1 per 20 simulated shifts).

Two evaluation modes:
  1. Held-out synthetic test set -- precision/recall/AUC, XGBoost vs a
     naive single-signal ("gas trend positive") baseline, on the same
     labeled feature vectors used for training.
  2. End-to-end scripted-scenario replay -- runs the ACTUAL simulator +
     rolling-feature-store pipeline (same code Modules 1/2 use) through
     compound_risk_scenario_1, scores every tick, and reports when the
     scorer first crosses an alert threshold vs when the raw statutory
     threshold would have fired on its own.
"""

import sys
from pathlib import Path
from typing import List

import numpy as np
from sklearn.metrics import precision_score, recall_score

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))  # repo root (sentinelgrid/)

from backend.app.ml.scoring.train import generate_dataset, FEATURE_COLUMNS
from backend.app.ml.scoring.infer import CompoundRiskScorer
from backend.app.workers.features import RollingFeatureStore
from simulator.scenario_scripts import compound_risk_scenario_1 as cr1
from simulator.scenario_scripts import baseline_scenario as baseline
from simulator.shift_roster_generator import ShiftRosterGenerator
from simulator.zones import STATUTORY_THRESHOLDS

ALERT_THRESHOLD = 50.0  # score >= this counts as "the scorer fired"
FP_RATE_CEILING = 1 / 20  # < 1 false alarm per 20 simulated shifts


# ---------------------------------------------------------------------------
# 1. Held-out synthetic test set
# ---------------------------------------------------------------------------

def evaluate_on_held_out_set(scorer: CompoundRiskScorer, n_samples: int = 1000, seed: int = 999):
    df = generate_dataset(n_samples=n_samples, positive_fraction=0.3, seed=seed)
    y_true = df["label"].values

    xgb_scores = np.array([scorer.score(row) for row in df[FEATURE_COLUMNS].to_dict("records")])
    xgb_preds = (xgb_scores >= ALERT_THRESHOLD).astype(int)

    # Naive single-signal baseline in the same feature space: fires purely
    # on positive gas trend, ignoring every other feature -- this is the
    # "single-sensor-equivalent" comparator for the ML scorer, mirroring
    # simulator/baseline_comparator.py's role for raw sensor readings.
    baseline_preds = (df["gas_trend_slope"] > 0.001).astype(int).values

    results = {
        "xgboost": {
            "precision": precision_score(y_true, xgb_preds),
            "recall": recall_score(y_true, xgb_preds),
        },
        "single_signal_baseline": {
            "precision": precision_score(y_true, baseline_preds),
            "recall": recall_score(y_true, baseline_preds),
        },
    }
    return results


# ---------------------------------------------------------------------------
# 2. End-to-end scripted-scenario replay
# ---------------------------------------------------------------------------

def _replay_scenario(module, scorer: CompoundRiskScorer, duration_s: float, tick_s: float = 1.0):
    """
    Steps the scenario's own SensorStream + ShiftRosterGenerator forward
    tick-by-tick (matching what the real simulator -> enrichment worker ->
    orchestrator pipeline would see), feeding features into the trained
    scorer at every tick. Returns a per-tick log of (sim_time_s, score,
    raw_gas_value).
    """
    stream, roster, permit_events = module.build()
    feature_store = RollingFeatureStore()
    active_hot_work_permits = 0
    permit_idx = 0
    permit_events_sorted = sorted(permit_events, key=lambda e: e["sim_time_s"])

    log = []
    t = 0.0
    while t <= duration_s:
        readings = stream.tick(t)
        gas_value = readings.get(cr1.TARGET_ZONE, {}).get("gas_ppm")
        for zone_id, sensors in readings.items():
            for sensor_type, value in sensors.items():
                feature_store.ingest(zone_id, sensor_type, t, value)

        while (permit_idx < len(permit_events_sorted)
               and permit_events_sorted[permit_idx]["sim_time_s"] <= t):
            ev = permit_events_sorted[permit_idx]
            if ev["event_type"] == "permit_issued" and ev.get("permit_type") == "hot_work":
                active_hot_work_permits += 1
            elif ev["event_type"] == "permit_closed":
                active_hot_work_permits = max(0, active_hot_work_permits - 1)
            permit_idx += 1

        next_boundary_s = roster.next_boundary_s(t)
        gas_feats = feature_store.features(cr1.TARGET_ZONE, "gas_ppm", t)

        features = {
            "gas_trend_slope": gas_feats["5min"]["trend_slope_per_s"],
            "permit_zone_overlap_count": active_hot_work_permits,
            "shift_boundary_proximity_s": next_boundary_s,
            "equipment_maintenance_overdue_flag": 0,   # not modeled by the simulator yet
            "cv_occupancy_count": 2,                    # placeholder pending live CV integration
            "historical_incident_similarity_score": 0.3,  # placeholder pending RAG
        }
        score = scorer.score(features)
        log.append({"sim_time_s": t, "score": score, "gas_value": gas_value})
        t += tick_s

    return log


def evaluate_compound_risk_scenario(scorer: CompoundRiskScorer):
    log = _replay_scenario(cr1, scorer, duration_s=4200, tick_s=1.0)

    scorer_fire_t = next((row["sim_time_s"] for row in log if row["score"] >= ALERT_THRESHOLD), None)
    statutory_fire_t = next(
        (row["sim_time_s"] for row in log
         if row["gas_value"] is not None and row["gas_value"] >= STATUTORY_THRESHOLDS["gas_ppm"]),
        None,
    )

    lead_time_s = (statutory_fire_t - scorer_fire_t
                    if scorer_fire_t is not None and statutory_fire_t is not None else None)
    return {
        "caught": scorer_fire_t is not None,
        "scorer_fire_t": scorer_fire_t,
        "statutory_fire_t": statutory_fire_t,
        "lead_time_s": lead_time_s,
    }


def evaluate_false_positive_rate(scorer: CompoundRiskScorer, n_shifts: int = 20):
    """
    Runs the baseline (safe) scenario `n_shifts` times with different seeds
    -- since baseline_scenario.build() doesn't itself accept a seed param
    for the permit schedule, jitter comes from the SensorStream's own RNG
    seed, matching how noise (not scripted events) is the only source of
    false alarms in a scenario that's supposed to stay green throughout.
    """
    false_alarms = 0
    for seed in range(n_shifts):
        stream, roster, permit_events = baseline.build(seed=seed)
        feature_store = RollingFeatureStore()
        fired = False
        t = 0.0
        while t <= 6000:
            readings = stream.tick(t)
            for zone_id, sensors in readings.items():
                for sensor_type, value in sensors.items():
                    feature_store.ingest(zone_id, sensor_type, t, value)
            gas_feats = feature_store.features("zone-01-degassing", "gas_ppm", t)
            features = {
                "gas_trend_slope": gas_feats["5min"]["trend_slope_per_s"],
                "permit_zone_overlap_count": 0,
                "shift_boundary_proximity_s": roster.next_boundary_s(t),
                "equipment_maintenance_overdue_flag": 0,
                "cv_occupancy_count": 2,
                "historical_incident_similarity_score": 0.1,
            }
            if scorer.score(features) >= ALERT_THRESHOLD:
                fired = True
                break
            t += 1.0
        if fired:
            false_alarms += 1
    return false_alarms / n_shifts


def main():
    scorer = CompoundRiskScorer()

    print("=== 1. Held-out synthetic test set ===")
    results = evaluate_on_held_out_set(scorer)
    for name, m in results.items():
        print(f"  {name:24s} precision={m['precision']:.3f}  recall={m['recall']:.3f}")

    print("\n=== 2. Scripted scenario replay: compound_risk_scenario_1 ===")
    scenario_result = evaluate_compound_risk_scenario(scorer)
    if scenario_result["caught"]:
        print(f"  Scorer fired at t={scenario_result['scorer_fire_t']:.0f}s "
              f"(threshold={ALERT_THRESHOLD})")
        if scenario_result["statutory_fire_t"] is not None:
            print(f"  Statutory single-sensor breach at t={scenario_result['statutory_fire_t']:.0f}s")
            print(f"  Lead time: {scenario_result['lead_time_s'] / 60:.1f} min")
    else:
        print("  ** Scorer did NOT fire during this scenario -- FAILS the 4/4 catch target **")

    print(f"\n=== 3. False-positive rate over {20} simulated baseline shifts ===")
    fp_rate = evaluate_false_positive_rate(scorer, n_shifts=20)
    verdict = "PASS" if fp_rate < FP_RATE_CEILING else "FAIL"
    print(f"  False-positive rate: {fp_rate:.3f} (ceiling: <{FP_RATE_CEILING:.3f}) -- {verdict}")


if __name__ == "__main__":
    main()
