"""
Single-sensor baseline comparator.

A minimal detector that only fires when a raw reading crosses its own
statutory threshold (no correlation, no trend, no multi-signal reasoning).
Run this side-by-side with the full SentinelGrid agent stack against the
same scenario feed to produce the lead-time / detection-accuracy numbers
for the demo (Member 1's cockpit displays these live).

Usage as a library:
    comparator = BaselineComparator()
    for sim_time_s, zone_id, sensor_type, value in feed:
        alert = comparator.check(sim_time_s, zone_id, sensor_type, value)
        if alert:
            ...

Usage as a CLI (reads a JSONL sensor-event log produced by plant_simulator.py
in --offline mode):
    python -m simulator.baseline_comparator path/to/sensors_ingest.jsonl
"""

import json
import sys
from dataclasses import dataclass
from typing import Optional

from .zones import STATUTORY_THRESHOLDS


@dataclass
class BaselineAlert:
    sim_time_s: float
    zone_id: str
    sensor_type: str
    value: float
    threshold: float


class BaselineComparator:
    def __init__(self, thresholds: dict = None):
        self.thresholds = thresholds or STATUTORY_THRESHOLDS
        self._already_fired = set()  # (zone_id, sensor_type) -> only fire once per breach episode

    def check(self, sim_time_s: float, zone_id: str, sensor_type: str,
              value: float) -> Optional[BaselineAlert]:
        threshold = self.thresholds.get(sensor_type)
        if threshold is None:
            return None
        key = (zone_id, sensor_type)
        if value >= threshold:
            if key in self._already_fired:
                return None
            self._already_fired.add(key)
            return BaselineAlert(sim_time_s, zone_id, sensor_type, value, threshold)
        else:
            self._already_fired.discard(key)
            return None


def run_from_jsonl(path: str):
    comparator = BaselineComparator()
    alerts = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            ev = json.loads(line)
            if ev.get("event_type") != "sensor_reading":
                continue
            alert = comparator.check(
                ev["sim_time_s"], ev["zone_id"], ev["sensor_type"], ev["value"]
            )
            if alert:
                alerts.append(alert)
                print(f"[BASELINE ALERT] t={alert.sim_time_s:.0f}s zone={alert.zone_id} "
                      f"{alert.sensor_type}={alert.value} (threshold={alert.threshold})")
    if not alerts:
        print("No baseline alerts fired.")
    return alerts


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m simulator.baseline_comparator <sensors_ingest.jsonl>")
        sys.exit(1)
    run_from_jsonl(sys.argv[1])
