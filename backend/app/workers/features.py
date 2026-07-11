"""
Rolling-window aggregate feature builder.

For each zone/sensor_type, maintains a time-ordered buffer of (sim_time_s,
value) readings and computes 5/15/60-min rolling aggregates: mean, max,
trend slope (linear regression slope, value-unit per second), and
drift-rate (slope normalized to value-unit per minute, easier to reason
about in agent rules like "gas trend slope positive").

These are the numbers written back onto the Zone node as updated
properties, and the trend-slope/drift-rate ones are exactly what the
Compound Risk Agent's pattern query and the XGBoost scorer consume.
"""

from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

WINDOW_SECONDS = {"5min": 300, "15min": 900, "60min": 3600}


@dataclass
class ZoneSensorBuffer:
    """Time-ordered (sim_time_s, value) buffer for one (zone_id, sensor_type)."""
    times: List[float] = field(default_factory=list)
    values: List[float] = field(default_factory=list)

    def add(self, sim_time_s: float, value: float):
        # Buffer is expected to receive readings in non-decreasing time order
        # (true for both the live stream and replay); append + trim is O(1)
        # amortized rather than re-sorting.
        self.times.append(sim_time_s)
        self.values.append(value)

    def trim_older_than(self, cutoff_s: float):
        idx = bisect_left(self.times, cutoff_s)
        if idx > 0:
            del self.times[:idx]
            del self.values[:idx]

    def window(self, sim_time_s: float, window_s: float) -> Tuple[List[float], List[float]]:
        cutoff = sim_time_s - window_s
        idx = bisect_left(self.times, cutoff)
        return self.times[idx:], self.values[idx:]


def _linear_slope(times: List[float], values: List[float]) -> float:
    """Least-squares slope (value-unit / second). Returns 0.0 for <2 points."""
    n = len(times)
    if n < 2:
        return 0.0
    mean_t = sum(times) / n
    mean_v = sum(values) / n
    num = sum((t - mean_t) * (v - mean_v) for t, v in zip(times, values))
    den = sum((t - mean_t) ** 2 for t in times)
    if den == 0:
        return 0.0
    return num / den


MIN_POINTS_FOR_TREND = 3      # a 2-point "slope" is just noise between two samples
MIN_SPAN_FRACTION_FOR_TREND = 0.9  # require the window to be ~fully populated before
                                     # trusting its slope. The regression's time-variance
                                     # denominator scales with span SQUARED, so a half-full
                                     # window isn't "half as noisy" -- it's ~4x noisier.
                                     # A slope estimated from 60s of a 300s window looked
                                     # fine on paper but was actually ~6x noisier than the
                                     # steady-state noise level the scorer was trained on,
                                     # causing false alarms during every window's fill-up period.


def compute_window_stats(times: List[float], values: List[float], window_s: float = None) -> dict:
    if not values:
        return {"mean": None, "max": None, "trend_slope_per_s": 0.0,
                "drift_rate_per_min": 0.0, "n": 0}
    span = times[-1] - times[0] if len(times) >= 2 else 0.0
    enough_points = len(values) >= MIN_POINTS_FOR_TREND
    # If window_s is known, require the buffer to actually span most of it
    # before trusting the slope (see note above). If window_s isn't given
    # (e.g. a caller testing the regression math directly against clean,
    # already-complete data), fall back to the point-count check alone.
    enough_span = (span >= window_s * MIN_SPAN_FRACTION_FOR_TREND) if window_s else True
    trustworthy = enough_points and enough_span
    slope_per_s = _linear_slope(times, values) if trustworthy else 0.0
    return {
        "mean": sum(values) / len(values),
        "max": max(values),
        "trend_slope_per_s": slope_per_s,
        "drift_rate_per_min": slope_per_s * 60.0,
        "n": len(values),
    }


class RollingFeatureStore:
    """
    Maintains per-(zone_id, sensor_type) buffers and computes 5/15/60-min
    rolling aggregates on demand. One instance lives for the lifetime of the
    enrichment worker process.
    """

    def __init__(self, windows: dict = None):
        self.windows = windows or WINDOW_SECONDS
        self._buffers: Dict[Tuple[str, str], ZoneSensorBuffer] = defaultdict(ZoneSensorBuffer)
        self._max_window_s = max(self.windows.values())

    def ingest(self, zone_id: str, sensor_type: str, sim_time_s: float, value: float):
        buf = self._buffers[(zone_id, sensor_type)]
        buf.add(sim_time_s, value)
        buf.trim_older_than(sim_time_s - self._max_window_s)

    def features(self, zone_id: str, sensor_type: str, sim_time_s: float) -> dict:
        buf = self._buffers.get((zone_id, sensor_type))
        out = {}
        for label, window_s in self.windows.items():
            times, values = ([], []) if buf is None else buf.window(sim_time_s, window_s)
            out[label] = compute_window_stats(times, values, window_s=window_s)
        return out

    def all_zone_features(self, zone_id: str, sim_time_s: float) -> Dict[str, dict]:
        out = {}
        for (zid, sensor_type) in list(self._buffers.keys()):
            if zid != zone_id:
                continue
            out[sensor_type] = self.features(zone_id, sensor_type, sim_time_s)
        return out
