"""
Baseline sensor-stream generator.

Produces gas/temp/pressure/vibration readings with realistic noise per zone,
at a 1Hz-equivalent simulated rate (one reading per simulated second per
sensor per zone), posted to /api/v1/sensors/ingest.

`speed` lets the CLI run many simulated seconds per wall-clock second so a
48-hour-feeling scenario can be demoed in minutes.
"""

import random
from typing import Callable, Dict, Optional

from .zones import ZONES, Zone

SENSOR_TYPES = ["gas_ppm", "temp_c", "pressure_kpa", "vibration_mm_s"]


class SensorStream:
    """
    Stateful per-zone sensor stream. Call `.tick(sim_time_s)` once per
    simulated second to get that second's readings for every zone.

    `drift_fn(zone_id, sensor_type, sim_time_s) -> float` is an optional
    hook scenarios use to inject a deliberate additive drift on top of the
    baseline+noise (e.g. the compound-risk gas-drift scenario).
    """

    def __init__(self, zones=ZONES, seed: Optional[int] = None,
                 drift_fn: Optional[Callable[[str, str, float], float]] = None):
        self.zones = zones
        self.rng = random.Random(seed)
        self.drift_fn = drift_fn or (lambda zone_id, sensor_type, t: 0.0)

    def _reading(self, zone: Zone, sensor_type: str, sim_time_s: float) -> float:
        mean, sigma = zone.baseline.get(sensor_type, (0.0, 0.0))
        noise = self.rng.gauss(0, sigma)
        drift = self.drift_fn(zone.zone_id, sensor_type, sim_time_s)
        value = max(0.0, mean + noise + drift)
        return round(value, 3)

    def tick(self, sim_time_s: float) -> Dict[str, dict]:
        """Returns {zone_id: {sensor_type: value, ...}, ...} for this instant."""
        out = {}
        for zone in self.zones:
            if not zone.baseline:
                continue
            out[zone.zone_id] = {
                sensor_type: self._reading(zone, sensor_type, sim_time_s)
                for sensor_type in SENSOR_TYPES
                if sensor_type in zone.baseline
            }
        return out

    def tick_events(self, sim_time_s: float, wall_clock_iso: str) -> list:
        """Same as tick() but flattened into individual ingest-ready event dicts."""
        events = []
        readings = self.tick(sim_time_s)
        for zone_id, sensors in readings.items():
            for sensor_type, value in sensors.items():
                events.append({
                    "event_type": "sensor_reading",
                    "zone_id": zone_id,
                    "sensor_type": sensor_type,
                    "value": value,
                    "sim_time_s": sim_time_s,
                    "timestamp": wall_clock_iso,
                })
        return events
