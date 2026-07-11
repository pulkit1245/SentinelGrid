"""
Time-alignment across heterogeneous sample rates.

Sensor readings arrive at ~1Hz-equivalent, CV occupancy counts might arrive
every 2-5 fps (very different real rate) and once-off permit/shift events
arrive sporadically. To correlate them (e.g. "gas trend AND cv occupancy AND
permit active, all true at the same moment") everything needs to land on a
common time grid first.

This module buckets raw events by (zone_id, bucket_start) at a configurable
grid resolution (default 60s, matching the smallest rolling-window size used
downstream) and reduces multiple readings landing in the same bucket to a
single representative value per sensor_type.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

DEFAULT_GRID_S = 60.0


@dataclass(frozen=True)
class GridBucket:
    zone_id: str
    bucket_start_s: float
    grid_s: float

    @property
    def bucket_end_s(self) -> float:
        return self.bucket_start_s + self.grid_s


def bucket_start(sim_time_s: float, grid_s: float = DEFAULT_GRID_S) -> float:
    return (sim_time_s // grid_s) * grid_s


def align_events(events: Iterable[dict], grid_s: float = DEFAULT_GRID_S,
                  reducer: str = "mean") -> Dict[GridBucket, Dict[str, float]]:
    """
    Buckets a stream of sensor_reading-shaped events
    ({zone_id, sensor_type, value, sim_time_s}) onto the common grid.

    Multiple readings in the same (zone, bucket, sensor_type) are reduced
    via `reducer` ("mean" | "last" | "max"). Returns:
        {GridBucket: {sensor_type: reduced_value, ...}, ...}

    Non-sensor events (permit/shift/cv) are handled by align_flag_events()
    below since they're presence-in-window rather than numeric-reduce.
    """
    raw: Dict[GridBucket, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for ev in events:
        if ev.get("event_type") != "sensor_reading":
            continue
        zone_id = ev["zone_id"]
        sensor_type = ev["sensor_type"]
        t = ev["sim_time_s"]
        bkt = GridBucket(zone_id, bucket_start(t, grid_s), grid_s)
        raw[bkt][sensor_type].append(ev["value"])

    out: Dict[GridBucket, Dict[str, float]] = {}
    for bkt, sensor_values in raw.items():
        out[bkt] = {}
        for sensor_type, values in sensor_values.items():
            if reducer == "mean":
                out[bkt][sensor_type] = sum(values) / len(values)
            elif reducer == "last":
                out[bkt][sensor_type] = values[-1]
            elif reducer == "max":
                out[bkt][sensor_type] = max(values)
            else:
                raise ValueError(f"Unknown reducer '{reducer}'")
    return out


def align_flag_events(events: Iterable[dict], grid_s: float = DEFAULT_GRID_S,
                       event_types: Optional[List[str]] = None) -> Dict[GridBucket, List[dict]]:
    """
    Buckets non-numeric events (permit_issued, cv detections, etc.) onto the
    same grid so a downstream feature builder can ask "was there a
    permit_issued event for this zone in this bucket?" without re-deriving
    bucket boundaries.
    """
    out: Dict[GridBucket, List[dict]] = defaultdict(list)
    for ev in events:
        et = ev.get("event_type")
        if event_types is not None and et not in event_types:
            continue
        if et == "sensor_reading":
            continue
        zone_id = ev.get("zone_id")
        if zone_id is None:
            continue  # plant-wide events (e.g. shift_boundary) handled separately
        t = ev["sim_time_s"]
        bkt = GridBucket(zone_id, bucket_start(t, grid_s), grid_s)
        out[bkt].append(ev)
    return out
