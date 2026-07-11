"""
Full precision/recall report vs. the single-sensor baseline.

Aggregates numbers from every module (Module 1's baseline comparator,
Module 5's scorer evaluation, this module's scenario-timing rehearsal) into
the single report Member 1's cockpit displays live during the demo. Prints
a human-readable summary and writes a JSON file for the cockpit to consume
directly.

Run with: python -m evaluation.full_report
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root

from backend.app.ml.scoring.evaluate import (
    evaluate_on_held_out_set, evaluate_compound_risk_scenario,
    evaluate_false_positive_rate, ALERT_THRESHOLD, FP_RATE_CEILING,
)
from backend.app.ml.scoring.infer import CompoundRiskScorer
from evaluation.scenario_rehearsal import rehearse, LEAD_TIME_MIN_S, LEAD_TIME_MAX_S

REPORT_PATH = Path(__file__).resolve().parent / "latest_report.json"


def build_report() -> dict:
    scorer = CompoundRiskScorer()

    held_out = evaluate_on_held_out_set(scorer)
    single_scenario = evaluate_compound_risk_scenario(scorer)
    fp_rate = evaluate_false_positive_rate(scorer, n_shifts=20)
    rehearsal_summary, _ = rehearse(n_runs=30)

    report = {
        "generated_by": "evaluation/full_report.py",
        "target_lead_time_window_min": [LEAD_TIME_MIN_S / 60, LEAD_TIME_MAX_S / 60],
        "alert_threshold": ALERT_THRESHOLD,
        "held_out_test_set": held_out,
        "single_scripted_scenario": {
            "caught": single_scenario["caught"],
            "lead_time_min": (single_scenario["lead_time_s"] / 60
                               if single_scenario["lead_time_s"] is not None else None),
        },
        "scenario_reliability_across_30_seeds": rehearsal_summary,
        "false_positive_rate_vs_ceiling": {
            "rate": fp_rate,
            "ceiling": FP_RATE_CEILING,
            "pass": fp_rate < FP_RATE_CEILING,
        },
        "overall_verdict": None,  # filled in below
    }

    checks = [
        report["held_out_test_set"]["xgboost"]["precision"] > 0.9,
        report["held_out_test_set"]["xgboost"]["recall"] > 0.9,
        report["single_scripted_scenario"]["caught"],
        report["scenario_reliability_across_30_seeds"]["pass_rate"] >= 0.9,
        report["false_positive_rate_vs_ceiling"]["pass"],
    ]
    report["overall_verdict"] = "READY FOR DEMO" if all(checks) else "NOT READY -- see failing sections above"
    return report


def print_report(report: dict):
    print("=" * 70)
    print("SENTINELGRID -- MODULE 2 PRECISION/RECALL REPORT")
    print("=" * 70)

    ho = report["held_out_test_set"]
    print("\n[Held-out synthetic test set]")
    print(f"  XGBoost scorer:            precision={ho['xgboost']['precision']:.3f}  "
          f"recall={ho['xgboost']['recall']:.3f}")
    print(f"  Single-signal baseline:    precision={ho['single_signal_baseline']['precision']:.3f}  "
          f"recall={ho['single_signal_baseline']['recall']:.3f}")

    ss = report["single_scripted_scenario"]
    print("\n[Scripted compound-risk scenario, single run]")
    print(f"  Caught: {ss['caught']}")
    if ss["lead_time_min"] is not None:
        lo, hi = report["target_lead_time_window_min"]
        print(f"  Lead time: {ss['lead_time_min']:.1f} min (target: {lo:.0f}-{hi:.0f} min)")

    rs = report["scenario_reliability_across_30_seeds"]
    print("\n[Scenario reliability across 30 seeds]")
    print(f"  In target window: {rs['n_in_target_window']}/{rs['n_runs']} ({rs['pass_rate']:.0%})")
    if rs["lead_time_mean_s"] is not None:
        print(f"  Lead time: mean={rs['lead_time_mean_s']/60:.1f}min  stdev={rs['lead_time_stdev_s']/60:.1f}min")

    fp = report["false_positive_rate_vs_ceiling"]
    print("\n[False-positive rate]")
    print(f"  Rate: {fp['rate']:.3f}  Ceiling: <{fp['ceiling']:.3f}  "
          f"{'PASS' if fp['pass'] else 'FAIL'}")

    print(f"\n{'=' * 70}")
    print(f"OVERALL VERDICT: {report['overall_verdict']}")
    print("=" * 70)


def main():
    report = build_report()
    print_report(report)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull JSON report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
