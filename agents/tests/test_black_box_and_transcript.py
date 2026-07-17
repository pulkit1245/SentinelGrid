"""
Tests for the Black Box Recorder and Agent Transcript features.

Run with: python -m pytest agents/tests/test_black_box_and_transcript.py -v
"""

import pytest

from ..graph_client import NetworkXGraphClient
from ..shared_blackboard import Blackboard
from ..compound_risk_agent import CompoundRiskAgent
from ..permit_intelligence_agent import PermitIntelligenceAgent
from ..orchestrator_agent import OrchestratorAgent
from ..black_box_recorder import BlackBoxRecorder
from ..agent_transcript import (
    build_transcript, build_transcript_from_entry,
    format_transcript_text, format_transcript_text_from_entry,
)

ZONE = "zone-01-degassing"


def make_orchestrator_with_recorder():
    recorder = BlackBoxRecorder()
    graph = NetworkXGraphClient()
    bb = Blackboard(graph)
    orch = OrchestratorAgent(bb, compound_risk_agent=CompoundRiskAgent(bb),
                              permit_intelligence_agent=PermitIntelligenceAgent(bb),
                              black_box_recorder=recorder)
    return orch, bb, recorder


# ---------------------------------------------------------------------------
# BlackBoxRecorder
# ---------------------------------------------------------------------------

def test_recorder_captures_every_cycle():
    orch, bb, recorder = make_orchestrator_with_recorder()
    bb.write_zone_properties(ZONE, {"gas_ppm_last_value": 8.0})
    bb.update_shift_state(next_boundary_s=6 * 3600, changeover_window_s=1800)

    orch.run_zone(ZONE, sim_time_s=0)
    orch.run_zone(ZONE, sim_time_s=60)
    orch.run_zone(ZONE, sim_time_s=120)

    assert len(recorder.entries) == 3
    assert [e.sim_time_s for e in recorder.entries] == [0, 60, 120]


def test_snapshot_at_returns_most_recent_entry_at_or_before_time():
    orch, bb, recorder = make_orchestrator_with_recorder()
    bb.write_zone_properties(ZONE, {"gas_ppm_last_value": 8.0})
    bb.update_shift_state(next_boundary_s=6 * 3600, changeover_window_s=1800)

    orch.run_zone(ZONE, sim_time_s=0)
    orch.run_zone(ZONE, sim_time_s=100)
    orch.run_zone(ZONE, sim_time_s=200)

    snap = recorder.snapshot_at(ZONE, sim_time_s=150)
    assert snap.sim_time_s == 100  # most recent entry AT OR BEFORE 150

    snap_exact = recorder.snapshot_at(ZONE, sim_time_s=200)
    assert snap_exact.sim_time_s == 200

    snap_before_any = recorder.snapshot_at(ZONE, sim_time_s=-10)
    assert snap_before_any is None


def test_decision_changes_only_returns_transitions():
    orch, bb, recorder = make_orchestrator_with_recorder()
    bb.write_zone_properties(ZONE, {"gas_ppm_last_value": 8.0})
    bb.update_shift_state(next_boundary_s=6 * 3600, changeover_window_s=1800)

    # 3 identical "clear" cycles, then a hard-rule breach -> "critical"
    orch.run_zone(ZONE, sim_time_s=0)
    orch.run_zone(ZONE, sim_time_s=60)
    orch.run_zone(ZONE, sim_time_s=120)
    bb.write_zone_properties(ZONE, {"gas_ppm_last_value": 30.0})  # breach
    orch.run_zone(ZONE, sim_time_s=180)
    orch.run_zone(ZONE, sim_time_s=240)  # still critical, not a NEW change

    changes = recorder.decision_changes(ZONE)
    assert [c.decision for c in changes] == ["clear", "critical"]
    assert [c.sim_time_s for c in changes] == [0, 180]


def test_recorder_save_and_load_round_trip(tmp_path):
    orch, bb, recorder = make_orchestrator_with_recorder()
    bb.write_zone_properties(ZONE, {"gas_ppm_last_value": 30.0})
    bb.update_shift_state(next_boundary_s=6 * 3600, changeover_window_s=1800)
    orch.run_zone(ZONE, sim_time_s=0)

    save_path = tmp_path / "black_box_test.jsonl"
    recorder.save(save_path)

    reloaded = BlackBoxRecorder.load(save_path)
    assert len(reloaded.entries) == 1
    assert reloaded.entries[0].zone_id == ZONE
    assert reloaded.entries[0].decision == "critical"
    assert reloaded.entries[0].hard_rule_violation["sensor_type"] == "gas_ppm"


# ---------------------------------------------------------------------------
# Agent Transcript
# ---------------------------------------------------------------------------

def test_transcript_reflects_hard_rule_escalation():
    orch, bb, _ = make_orchestrator_with_recorder()
    bb.write_zone_properties(ZONE, {"gas_ppm_last_value": 30.0})
    bb.update_shift_state(next_boundary_s=6 * 3600, changeover_window_s=1800)
    state = orch.run_zone(ZONE, sim_time_s=0)

    text = format_transcript_text(state)
    assert "Hard-Rules Check" in text
    assert "breached" in text
    assert "CRITICAL" in text


def test_transcript_reflects_clear_state():
    orch, bb, _ = make_orchestrator_with_recorder()
    bb.write_zone_properties(ZONE, {"gas_ppm_last_value": 8.0})
    bb.update_shift_state(next_boundary_s=6 * 3600, changeover_window_s=1800)
    state = orch.run_zone(ZONE, sim_time_s=0)

    lines = build_transcript(state)
    speakers = [ln.speaker for ln in lines]
    assert "Orchestrator" in speakers
    orchestrator_line = next(ln for ln in lines if ln.speaker == "Orchestrator")
    assert "all clear" in orchestrator_line.message.lower()


def test_transcript_from_entry_matches_live_transcript_content():
    """
    The replay-from-disk transcript (from_entry) should tell the same
    STORY as the live transcript for the exact same underlying decision --
    this is what makes "replay after the fact" trustworthy.
    """
    orch, bb, recorder = make_orchestrator_with_recorder()
    bb.write_zone_properties(ZONE, {"gas_ppm_last_value": 30.0})
    bb.update_shift_state(next_boundary_s=6 * 3600, changeover_window_s=1800)
    live_state = orch.run_zone(ZONE, sim_time_s=0)

    entry = recorder.entries[0]
    live_text = format_transcript_text(live_state)
    replay_text = format_transcript_text_from_entry(entry)

    assert "CRITICAL" in live_text and "CRITICAL" in replay_text
    assert "breached" in live_text and "breached" in replay_text


def test_transcript_from_entry_works_after_save_and_reload(tmp_path):
    """
    The whole point of the black box: even after the original agent
    objects are gone (process restarted, log reloaded from disk), the
    transcript must still be reconstructable from the saved summary alone.
    """
    orch, bb, recorder = make_orchestrator_with_recorder()
    bb.write_zone_properties(ZONE, {"gas_ppm_last_value": 30.0})
    bb.update_shift_state(next_boundary_s=6 * 3600, changeover_window_s=1800)
    orch.run_zone(ZONE, sim_time_s=0)

    save_path = tmp_path / "black_box_test.jsonl"
    recorder.save(save_path)
    reloaded = BlackBoxRecorder.load(save_path)

    text = format_transcript_text_from_entry(reloaded.entries[0])
    assert "CRITICAL" in text
    assert "Compound Risk Agent" in text
    assert "Permit Intelligence Agent" in text
