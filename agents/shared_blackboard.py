"""
Shared blackboard client.

Thin wrapper agents use to read/write Zone/Permit/Sensor state from the
Plant Risk Graph, without each agent needing to know graph-client
implementation details (Neo4j vs networkx fallback) or re-derive common
queries like "gas trend slope for this zone" from raw properties.

All agents (Compound Risk, Permit Intelligence, Orchestrator) hold one
Blackboard instance wrapping the same underlying graph_client, so writes
from one agent are immediately visible to the others within a cycle.
"""

from dataclasses import dataclass
from typing import List, Optional

from .graph_client import GraphClientBase, Permit


@dataclass
class ZoneSnapshot:
    zone_id: str
    properties: dict
    active_permits: List[Permit]

    def sensor_value(self, sensor_type: str, default=None):
        return self.properties.get(f"{sensor_type}_last_value", default)

    def trend_slope(self, sensor_type: str, window: str = "5min", default=0.0):
        return self.properties.get(f"{sensor_type}_{window}_slope_per_s", default)

    def drift_rate_per_min(self, sensor_type: str, default=0.0):
        return self.properties.get(f"{sensor_type}_drift_rate_per_min", default)

    def anomaly_score(self, sensor_type: str, default=0.0):
        return self.properties.get(f"{sensor_type}_anomaly_score", default)

    def has_active_permit_type(self, permit_type: str) -> bool:
        return any(p.permit_type == permit_type for p in self.active_permits)


class Blackboard:
    def __init__(self, graph_client: GraphClientBase, shift_state: Optional[dict] = None):
        """
        shift_state is set externally (by whatever consumes shift_boundary /
        changeover_window_start events -- currently the orchestrator loop)
        since shift schedule is plant-wide, not per-zone graph state:
            {"next_boundary_s": float, "in_changeover_window": bool}
        """
        self.graph = graph_client
        self.shift_state = shift_state or {"next_boundary_s": None, "in_changeover_window": False}

    def snapshot(self, zone_id: str) -> ZoneSnapshot:
        return ZoneSnapshot(
            zone_id=zone_id,
            properties=self.graph.get_zone_properties(zone_id),
            active_permits=self.graph.active_permits(zone_id),
        )

    def all_zone_ids(self) -> List[str]:
        return self.graph.zone_ids()

    def update_shift_state(self, next_boundary_s: float, changeover_window_s: float):
        self.shift_state = {
            "next_boundary_s": next_boundary_s,
            "in_changeover_window": 0 <= next_boundary_s <= changeover_window_s,
        }

    def write_zone_properties(self, zone_id: str, properties: dict):
        self.graph.update_zone_properties(zone_id, properties)

    def record_event(self, event: dict):
        self.graph.record_event(event)
