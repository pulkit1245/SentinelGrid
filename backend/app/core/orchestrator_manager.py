"""
orchestrator_manager.py — Central Manager for OrchestratorAgent and BlackBoxRecorder.

Maintains the live Blackboard, CompoundRiskAgent, PermitIntelligenceAgent,
BlackBoxRecorder, and OrchestratorAgent in-memory for the application lifetime.
"""
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.graph_client import NetworkXGraphClient
from agents.shared_blackboard import Blackboard
from agents.compound_risk_agent import CompoundRiskAgent
from agents.permit_intelligence_agent import PermitIntelligenceAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.black_box_recorder import BlackBoxRecorder, BlackBoxEntry
from agents.agent_transcript import (
    format_transcript_markdown,
    build_transcript,
    build_transcript_from_entry,
    TranscriptLine,
)
from backend.app.workers.features import RollingFeatureStore
from simulator.scenario_scripts import compound_risk_scenario_1 as cr1

logger = logging.getLogger("sentinelgrid.orchestrator_manager")


class OrchestratorManager:
    def __init__(self):
        self.graph = NetworkXGraphClient()
        self.bb = Blackboard(self.graph)
        self.compound_risk_agent = CompoundRiskAgent(self.bb)
        self.permit_intelligence_agent = PermitIntelligenceAgent(self.bb)
        self.black_box = BlackBoxRecorder()

        # Wire OrchestratorAgent with BlackBoxRecorder attached!
        self.orchestrator = OrchestratorAgent(
            blackboard=self.bb,
            compound_risk_agent=self.compound_risk_agent,
            permit_intelligence_agent=self.permit_intelligence_agent,
            black_box_recorder=self.black_box,
        )

        self.seeded = False
        # Pre-seed default scenario data in background/initially so UI has rich historical replay
        self.seed_default_scenario()

    def seed_default_scenario(self, target_zone: str = cr1.TARGET_ZONE):
        """Run compound_risk_scenario_1 through the pipeline to populate historical story beats."""
        try:
            logger.info("Seeding Orchestrator simulation scenario for zone: %s", target_zone)
            stream, roster, permit_events = cr1.build()
            feature_store = RollingFeatureStore()
            permit_sorted = sorted(permit_events, key=lambda e: e["sim_time_s"])
            permit_idx = 0

            tick_s = 30.0
            duration_s = 4200.0
            t = 0.0

            while t <= duration_s:
                readings = stream.tick(t)
                for zone_id, sensors in readings.items():
                    for sensor_type, value in sensors.items():
                        feature_store.ingest(zone_id, sensor_type, t, value)
                        feats = feature_store.features(zone_id, sensor_type, t)
                        self.bb.write_zone_properties(zone_id, {
                            f"{sensor_type}_last_value": value,
                            f"{sensor_type}_5min_slope_per_s": feats["5min"]["trend_slope_per_s"],
                        })

                while permit_idx < len(permit_sorted) and permit_sorted[permit_idx]["sim_time_s"] <= t:
                    self.bb.record_event(permit_sorted[permit_idx])
                    permit_idx += 1

                self.bb.update_shift_state(roster.next_boundary_s(t), roster.changeover_window_s)
                self.orchestrator.run_zone(target_zone, sim_time_s=t)
                t += tick_s

            self.seeded = True
            logger.info(
                "Successfully seeded %d black-box entries for %s",
                len(self.black_box.timeline_for_zone(target_zone)),
                target_zone,
            )
        except Exception as e:
            logger.error("Error seeding default scenario: %s", e, exc_info=True)

    def run_zone(self, zone_id: str, sim_time_s: Optional[float] = None) -> Dict[str, Any]:
        """Runs the orchestrator agent for a given zone and logs to BlackBoxRecorder."""
        return self.orchestrator.run_zone(zone_id, sim_time_s=sim_time_s)

    def get_black_box_timeline(self, zone_id: str) -> List[Dict[str, Any]]:
        """Full historical timeline entries for a zone."""
        entries = self.black_box.timeline_for_zone(zone_id)
        if not entries and not self.seeded:
            self.seed_default_scenario()
            entries = self.black_box.timeline_for_zone(zone_id)

        return [
            {
                "sim_time_s": e.sim_time_s,
                "zone_id": e.zone_id,
                "hard_rule_violation": e.hard_rule_violation,
                "compound_finding_summary": e.compound_finding_summary,
                "permit_violations_summary": e.permit_violations_summary,
                "corroborating_signals": e.corroborating_signals,
                "decision": e.decision,
                "dispatched": e.dispatched,
            }
            for e in entries
        ]

    def get_black_box_story_beats(self, zone_id: str) -> List[Dict[str, Any]]:
        """Only the moments when decision actually changed."""
        entries = self.black_box.decision_changes(zone_id)
        if not entries and not self.seeded:
            self.seed_default_scenario()
            entries = self.black_box.decision_changes(zone_id)

        return [
            {
                "sim_time_s": e.sim_time_s,
                "zone_id": e.zone_id,
                "hard_rule_violation": e.hard_rule_violation,
                "compound_finding_summary": e.compound_finding_summary,
                "permit_violations_summary": e.permit_violations_summary,
                "corroborating_signals": e.corroborating_signals,
                "decision": e.decision,
                "dispatched": e.dispatched,
            }
            for e in entries
        ]

    def get_agent_transcript(self, zone_id: str, sim_time_s: Optional[float] = None) -> Dict[str, Any]:
        """
        Returns transcript for a specific simulation time (from historical entry)
        or runs a fresh orchestrator turn.
        """
        if sim_time_s is not None:
            snapshot = self.black_box.snapshot_at(zone_id, sim_time_s)
            if snapshot:
                lines = build_transcript_from_entry(snapshot)
                md = "\n\n".join(f"**{ln.speaker}:** {ln.message}" for ln in lines)
                return {
                    "zone_id": zone_id,
                    "sim_time_s": snapshot.sim_time_s,
                    "decision": snapshot.decision,
                    "transcript": md,
                    "lines": [{"speaker": ln.speaker, "message": ln.message} for ln in lines],
                }

        # Otherwise live/current state
        latest_state = self.orchestrator.run_zone(zone_id)
        lines = build_transcript(latest_state)
        return {
            "zone_id": zone_id,
            "sim_time_s": sim_time_s,
            "decision": latest_state.get("decision", "clear"),
            "transcript": format_transcript_markdown(latest_state),
            "lines": [{"speaker": ln.speaker, "message": ln.message} for ln in lines],
        }


# Global singleton instance
orchestrator_manager = OrchestratorManager()
