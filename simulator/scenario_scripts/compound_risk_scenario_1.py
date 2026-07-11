"""
Scripted compound-risk demo scenario.

Timeline (sim seconds, t=0 is scenario start):
  t=1200 (20:00)  Hot-work permit issued in zone-01-degassing
  t=1800 (30:00)  Gas reading in zone-01 begins a slow upward drift
  t=1800 (30:00)  Shift-changeover window opens (boundary at t=3600)
                  -> from this point all three compound-risk conditions
                     (hot-work permit active, positive gas-trend slope,
                     shift boundary within 30 min) are simultaneously true
  t=3600 (60:00)  Shift boundary itself
  t~3500 (58:20)  Gas reading would cross the single-sensor statutory
                  threshold (25 ppm) on its own

This gives a compound-risk detection lead time of ~1700s (~28 min) vs the
single-sensor baseline comparator, inside the target 15-45 min window.
Tune DRIFT_SLOPE_PPM_PER_S to shift that lead time if the target window
needs adjusting after end-to-end rehearsal.
"""

from ..sensor_stream import SensorStream
from ..shift_roster_generator import ShiftRosterGenerator
from ..zones import STATUTORY_THRESHOLDS

SCENARIO_NAME = "compound_risk_1"

TARGET_ZONE = "zone-01-degassing"
PERMIT_ISSUED_T = 1200
DRIFT_START_T = 1800
DRIFT_SLOPE_PPM_PER_S = 0.01  # (25 - 8) ppm / 0.01 ppm/s = 1700s to breach
SHIFT_LENGTH_S = 7200
CHANGEOVER_WINDOW_S = 1800
SHIFT_SIM_START_OFFSET_S = 3600  # phases the boundary to land at t=3600

# Sanity-check the scripted lead time at import time so a bad slope edit
# fails fast instead of silently drifting the demo out of spec.
_gas_baseline_mean = 8.0
_time_to_breach = (STATUTORY_THRESHOLDS["gas_ppm"] - _gas_baseline_mean) / DRIFT_SLOPE_PPM_PER_S
_breach_t = DRIFT_START_T + _time_to_breach
_lead_time_s = _breach_t - DRIFT_START_T
assert 15 * 60 <= _lead_time_s <= 45 * 60, (
    f"Scripted lead time {_lead_time_s / 60:.1f} min is outside the 15-45 min "
    "target window -- adjust DRIFT_SLOPE_PPM_PER_S."
)


def gas_drift(zone_id: str, sensor_type: str, sim_time_s: float) -> float:
    if zone_id != TARGET_ZONE or sensor_type != "gas_ppm":
        return 0.0
    if sim_time_s < DRIFT_START_T:
        return 0.0
    return DRIFT_SLOPE_PPM_PER_S * (sim_time_s - DRIFT_START_T)


def build(seed: int = 7):
    """Returns (SensorStream, ShiftRosterGenerator, permit_events) for this scenario."""
    stream = SensorStream(seed=seed, drift_fn=gas_drift)
    roster = ShiftRosterGenerator(
        shift_length_s=SHIFT_LENGTH_S,
        changeover_window_s=CHANGEOVER_WINDOW_S,
        sim_start_offset_s=SHIFT_SIM_START_OFFSET_S,
    )
    permit_events = [
        {"sim_time_s": PERMIT_ISSUED_T, "event_type": "permit_issued", "permit_type": "hot_work",
         "zone_id": TARGET_ZONE, "permit_id": "PMT-CR1-001"},
        # Left open deliberately -- the demo's point is that the permit
        # was valid *when issued* but conditions changed underneath it.
    ]
    return stream, roster, permit_events


def expected_lead_time_s() -> float:
    return _lead_time_s
