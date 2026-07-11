"""
Baseline scenario: all zones run at their resting baseline with normal
sensor noise, permits are issued/closed normally, shifts change over
normally -- nothing should ever escalate to "critical". This is the
"should stay green" negative-control scenario used in agent tests
and to establish the single-sensor baseline's false-positive rate.
"""

from ..sensor_stream import SensorStream
from ..shift_roster_generator import ShiftRosterGenerator

SCENARIO_NAME = "baseline"


def no_drift(zone_id, sensor_type, sim_time_s):
    return 0.0


def build(seed: int = 42):
    """Returns (SensorStream, ShiftRosterGenerator, permit_events) for this scenario."""
    stream = SensorStream(seed=seed, drift_fn=no_drift)
    roster = ShiftRosterGenerator()
    # A couple of routine, low-risk permits with no zone overlap conflicts.
    permit_events = [
        {"sim_time_s": 300, "event_type": "permit_issued", "permit_type": "cold_work",
         "zone_id": "zone-06-control", "permit_id": "PMT-BASE-001"},
        {"sim_time_s": 5400, "event_type": "permit_closed",
         "zone_id": "zone-06-control", "permit_id": "PMT-BASE-001"},
    ]
    return stream, roster, permit_events
