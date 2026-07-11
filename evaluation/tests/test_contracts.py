"""
Contract tests.

Runs the ACTUAL simulator and CV pipeline (not synthetic mock events) and
validates every event they emit against EVENT_SCHEMAS. This is the concrete
version of "support integration debugging / fix event-shape mismatches" --
catching a shape mismatch here, before merge day, is a lot cheaper than
catching it while pairing with Member 1 live.

Run with: python -m pytest evaluation/tests/test_contracts.py -v
"""

import numpy as np
import pytest

from ..event_schemas import validate_event, validate_stream, SchemaViolation
from simulator.scenario_scripts import baseline_scenario, compound_risk_scenario_1
from simulator.ingest_client import IngestClient
from cv.frame_ingestor import SyntheticZoneIngestor
from cv.pipeline import ZoneCVPipeline


# ---------------------------------------------------------------------------
# Simulator events
# ---------------------------------------------------------------------------

def _collect_simulator_events(module, duration_s: float, tick_s: float = 30.0):
    """
    Runs a scenario module's generators directly (bypassing the network/CLI
    layer) and collects every event dict exactly as IngestClient.post_*
    would have serialized it, for schema validation.
    """
    stream, roster, permit_events = module.build()
    events = []
    permit_idx = 0
    permit_sorted = sorted(permit_events, key=lambda e: e["sim_time_s"])

    t = 0.0
    while t <= duration_s:
        for ev in stream.tick_events(t, "2026-07-09T00:00:00Z"):
            events.append(ev)
        for shift_ev in roster.events_up_to(t):
            events.append(roster.to_event_dict(shift_ev, "2026-07-09T00:00:00Z"))
        while permit_idx < len(permit_sorted) and permit_sorted[permit_idx]["sim_time_s"] <= t:
            ev = dict(permit_sorted[permit_idx])
            ev["timestamp"] = "2026-07-09T00:00:00Z"
            events.append(ev)
            permit_idx += 1
        t += tick_s

    return events


def test_baseline_scenario_events_match_schema():
    events = _collect_simulator_events(baseline_scenario, duration_s=6000)
    assert len(events) > 0
    failures = validate_stream(events)
    assert failures == {}, f"Schema failures in baseline_scenario events: {failures}"


def test_compound_risk_scenario_events_match_schema():
    events = _collect_simulator_events(compound_risk_scenario_1, duration_s=4200)
    assert len(events) > 0
    failures = validate_stream(events)
    assert failures == {}, f"Schema failures in compound_risk_scenario_1 events: {failures}"


def test_compound_risk_scenario_includes_expected_event_types():
    """
    A schema-valid stream that's missing an entire event TYPE is still a
    real integration bug (e.g. Member 1's cockpit expecting a permit_issued
    event that never actually arrives) -- checked here explicitly rather
    than relying on per-field validation alone to catch it.
    """
    events = _collect_simulator_events(compound_risk_scenario_1, duration_s=4200)
    event_types_seen = {ev["event_type"] for ev in events}
    assert "sensor_reading" in event_types_seen
    assert "permit_issued" in event_types_seen
    assert "shift_boundary" in event_types_seen
    assert "changeover_window_start" in event_types_seen


# ---------------------------------------------------------------------------
# CV pipeline events
# ---------------------------------------------------------------------------

class _RecordingIngestClient(IngestClient):
    """Captures every posted event in-memory instead of writing to disk, for inspection."""

    def __init__(self):
        super().__init__(offline=True)
        self.recorded = []

    def post(self, path, payload):
        self.recorded.append(payload)
        return True


def test_cv_pipeline_events_match_schema():
    class _FakeDetector:
        def detect(self, frame_bgr):
            return []  # empty detections -- we're validating event SHAPE, not detection accuracy here

    client = _RecordingIngestClient()
    pipeline = ZoneCVPipeline("zone-02-castfloor", detector=_FakeDetector(),
                               ingest_client=client, save_snapshots=False)
    ingestor = SyntheticZoneIngestor("zone-02-castfloor", num_frames=5, seed=3)

    list(pipeline.run(ingestor.frames()))

    assert len(client.recorded) > 0
    for ev in client.recorded:
        # the recorded payload includes IngestClient's own "_emitted_at" field,
        # which isn't part of the domain schema -- strip it before validating.
        clean = {k: v for k, v in ev.items() if k != "_emitted_at"}
        validate_event(clean)  # raises SchemaViolation on failure


# ---------------------------------------------------------------------------
# Schema validator itself
# ---------------------------------------------------------------------------

def test_validator_catches_missing_required_field():
    bad_event = {"event_type": "sensor_reading", "zone_id": "z1", "sensor_type": "gas_ppm",
                 "value": 8.0}  # missing sim_time_s and timestamp
    with pytest.raises(SchemaViolation):
        validate_event(bad_event)


def test_validator_catches_wrong_type():
    bad_event = {"event_type": "sensor_reading", "zone_id": "z1", "sensor_type": "gas_ppm",
                 "value": "eight",  # should be numeric
                 "sim_time_s": 10, "timestamp": "2026-01-01T00:00:00Z"}
    with pytest.raises(SchemaViolation):
        validate_event(bad_event)


def test_validator_catches_unknown_event_type():
    with pytest.raises(SchemaViolation):
        validate_event({"event_type": "totally_made_up_event"})
