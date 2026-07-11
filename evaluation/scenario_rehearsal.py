"""
Scripted-scenario timing rehearsal.

The Module 1 assertion (`compound_risk_scenario_1.py`'s import-time check)
only proves the lead time is correct for the NOISE-FREE drift math. The
actual simulator adds gaussian sensor noise, so the real single-sensor
breach time -- and therefore the real lead time -- varies run to run.
This rehearses the scenario across many seeds and confirms the 15-45 min
target holds up reliably, not just for the one seed anyone happened to
demo with locally.

This is the concrete version of the Module 6 checklist item: "Confirm the
compound-risk scenario reliably produces the target 15-45 min lead-time
window on the deployed (not just local) stack" -- "deployed" isn't
available in this environment, but "reliably ... not just local" is
exactly what running N seeds checks for.
"""

import statistics
from typing import List

from simulator.scenario_scripts import compound_risk_scenario_1 as cr1
from simulator.zones import STATUTORY_THRESHOLDS

TARGET_ZONE = cr1.TARGET_ZONE
LEAD_TIME_MIN_S = 15 * 60
LEAD_TIME_MAX_S = 45 * 60


def _single_run_lead_time_s(seed: int, duration_s: float = 4200, tick_s: float = 1.0) -> dict:
    """
    Runs the scenario's raw sensor stream (same source the enrichment
    worker and scorer consume) and finds when the statutory threshold is
    actually crossed by the noisy signal, vs. the scripted overlap-window
    start (t=DRIFT_START_T, when permit+drift+shift-window all become true).
    """
    stream, roster, permit_events = cr1.build(seed=seed)
    overlap_start_s = cr1.DRIFT_START_T  # scripted, deterministic regardless of noise seed

    statutory_fire_t = None
    t = 0.0
    while t <= duration_s:
        readings = stream.tick(t)
        gas_value = readings.get(TARGET_ZONE, {}).get("gas_ppm")
        if gas_value is not None and gas_value >= STATUTORY_THRESHOLDS["gas_ppm"]:
            statutory_fire_t = t
            break
        t += tick_s

    lead_time_s = (statutory_fire_t - overlap_start_s) if statutory_fire_t is not None else None
    return {
        "seed": seed,
        "overlap_start_s": overlap_start_s,
        "statutory_fire_t": statutory_fire_t,
        "lead_time_s": lead_time_s,
        "in_target_window": (lead_time_s is not None
                              and LEAD_TIME_MIN_S <= lead_time_s <= LEAD_TIME_MAX_S),
    }


def rehearse(n_runs: int = 30, duration_s: float = 4200) -> dict:
    runs = [_single_run_lead_time_s(seed, duration_s=duration_s) for seed in range(n_runs)]

    never_fired = [r for r in runs if r["statutory_fire_t"] is None]
    fired = [r for r in runs if r["statutory_fire_t"] is not None]
    lead_times = [r["lead_time_s"] for r in fired]
    in_window = [r for r in fired if r["in_target_window"]]

    summary = {
        "n_runs": n_runs,
        "n_never_fired": len(never_fired),
        "n_fired": len(fired),
        "n_in_target_window": len(in_window),
        "pass_rate": len(in_window) / n_runs,
        "lead_time_mean_s": statistics.mean(lead_times) if lead_times else None,
        "lead_time_stdev_s": statistics.stdev(lead_times) if len(lead_times) > 1 else None,
        "lead_time_min_s": min(lead_times) if lead_times else None,
        "lead_time_max_s": max(lead_times) if lead_times else None,
        "failing_seeds": [r["seed"] for r in runs if not r["in_target_window"]],
    }
    return summary, runs


def main():
    print(f"Rehearsing compound_risk_scenario_1 across seeds 0..29 "
          f"(target lead time: {LEAD_TIME_MIN_S/60:.0f}-{LEAD_TIME_MAX_S/60:.0f} min)...\n")
    summary, runs = rehearse(n_runs=30)

    print(f"Runs: {summary['n_runs']}")
    print(f"  Never crossed statutory threshold within scenario duration: {summary['n_never_fired']}")
    print(f"  Fired: {summary['n_fired']}")
    print(f"  Within 15-45 min target window: {summary['n_in_target_window']} "
          f"({summary['pass_rate']:.0%})")
    if summary["lead_time_mean_s"] is not None:
        print(f"  Lead time: mean={summary['lead_time_mean_s']/60:.1f}min "
              f"stdev={summary['lead_time_stdev_s']/60:.1f}min "
              f"range=[{summary['lead_time_min_s']/60:.1f}, {summary['lead_time_max_s']/60:.1f}]min")
    if summary["failing_seeds"]:
        print(f"  ** Seeds outside target window: {summary['failing_seeds']} **")

    verdict = "RELIABLE" if summary["pass_rate"] >= 0.9 else "NOT RELIABLE ENOUGH"
    print(f"\nVerdict: {verdict} (need >=90% of runs in-window to trust this for the live demo)")


if __name__ == "__main__":
    main()
