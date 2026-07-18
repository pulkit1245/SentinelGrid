"""
Black Box + Agent Transcript demo.

Runs compound_risk_scenario_1 through the ACTUAL pipeline (sensor stream ->
rolling features -> blackboard -> agents -> orchestrator), recording every
decision into a BlackBoxRecorder as it happens. At the end, replays the
"story beats" (moments the decision changed) as a readable agent
conversation -- this is the concrete demo of both new features together.

Run with: python -m evaluation.black_box_demo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root

from agents.graph_client import NetworkXGraphClient
from agents.shared_blackboard import Blackboard
from agents.compound_risk_agent import CompoundRiskAgent
from agents.permit_intelligence_agent import PermitIntelligenceAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.black_box_recorder import BlackBoxRecorder
from agents.agent_transcript import format_transcript_text, format_transcript_text_from_entry

from backend.app.workers.features import RollingFeatureStore
from simulator.scenario_scripts import compound_risk_scenario_1 as cr1

TARGET_ZONE = cr1.TARGET_ZONE
TICK_S = 30.0
DURATION_S = 4200.0


def run_demo():
    graph = NetworkXGraphClient()
    bb = Blackboard(graph)
    cr_agent = CompoundRiskAgent(bb)
    pi_agent = PermitIntelligenceAgent(bb)
    recorder = BlackBoxRecorder()
    orchestrator = OrchestratorAgent(
        bb, compound_risk_agent=cr_agent, permit_intelligence_agent=pi_agent,
        black_box_recorder=recorder,
    )

    stream, roster, permit_events = cr1.build()
    feature_store = RollingFeatureStore()
    permit_sorted = sorted(permit_events, key=lambda e: e["sim_time_s"])
    permit_idx = 0

    print(f"Running compound_risk_scenario_1 (zone={TARGET_ZONE}), recording every cycle...\n")

    last_state = None
    t = 0.0
    while t <= DURATION_S:
        readings = stream.tick(t)
        for zone_id, sensors in readings.items():
            for sensor_type, value in sensors.items():
                feature_store.ingest(zone_id, sensor_type, t, value)
                feats = feature_store.features(zone_id, sensor_type, t)
                bb.write_zone_properties(zone_id, {
                    f"{sensor_type}_last_value": value,
                    f"{sensor_type}_5min_slope_per_s": feats["5min"]["trend_slope_per_s"],
                })

        while permit_idx < len(permit_sorted) and permit_sorted[permit_idx]["sim_time_s"] <= t:
            bb.record_event(permit_sorted[permit_idx])
            permit_idx += 1

        bb.update_shift_state(roster.next_boundary_s(t), roster.changeover_window_s)

        last_state = orchestrator.run_zone(TARGET_ZONE, sim_time_s=t)
        t += TICK_S

    # ---- Feature 1: Black Box replay -- only the moments the decision changed ----
    print("=" * 70)
    print("BLACK BOX REPLAY -- story beats (moments the decision changed)")
    print("=" * 70)
    changes = recorder.decision_changes(TARGET_ZONE)
    for entry in changes:
        minutes = entry.sim_time_s / 60
        print(f"\n--- t={minutes:.1f} min -- decision became '{entry.decision.upper()}' ---")

    # ---- Feature 2: Agent debate transcript, at the moment escalation happened ----
    critical_entries = [e for e in changes if e.decision == "critical"]
    if critical_entries:
        first_escalation = critical_entries[0]
        print(f"\n{'=' * 70}")
        print(f"AGENT TRANSCRIPT -- at the moment of escalation "
              f"(t={first_escalation.sim_time_s / 60:.1f} min)")
        print("=" * 70)
        # IMPORTANT: this reads the actual RECORDED snapshot from that
        # historical tick (build_transcript_from_entry), not a fresh
        # orchestrator run -- re-running the agents now would reflect
        # whatever the blackboard's CURRENT (end-of-scenario) state is,
        # which is a different moment in time than the one we're labeling.
        print()
        print(format_transcript_text_from_entry(first_escalation))
    else:
        print("\n(No escalation occurred in this run.)")

    print(f"\n{'=' * 70}")
    print(f"Total cycles recorded: {len(recorder.entries)}")
    recorder.save()
    print(f"Full black-box log saved to agents/_black_box_log.jsonl "
          f"(reloadable via BlackBoxRecorder.load() for later replay)")


if __name__ == "__main__":
    run_demo()
