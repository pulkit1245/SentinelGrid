"""
Digital Permit Intelligence Agent.

Validates every active permit against live zone conditions:
  1. At issuance -- checked the moment a permit_issued event is recorded
     (validate_on_issue), so an obviously-invalid permit (e.g. hot work
     already-elevated gas in its own zone) gets flagged immediately rather
     than waiting for the next enrichment cycle.
  2. Continuously -- re-validated every agent cycle (revalidate_all), since
     conditions can change *after* a permit was validly issued (this is
     the scenario the compound-risk demo scripts: valid at t=1200, invalid
     by t=1800+ as gas drifts up).

Also flags hot work within a configurable hop-radius of elevated gas
readings in *neighboring* zones, using the ZONE_ADJACENCY hop-graph as a
stand-in for physical distance until real floor-plan coordinates exist.
"""

from dataclasses import dataclass
from typing import List, Optional

from .shared_blackboard import Blackboard
from .graph_client import Permit
from simulator.zones import STATUTORY_THRESHOLDS, zones_within_radius

GAS_CAUTION_FRACTION = 0.6  # flag hot work once gas is at 60% of the statutory threshold, not just past it
DEFAULT_RADIUS_HOPS = 1


@dataclass
class PermitViolation:
    permit_id: str
    zone_id: str
    permit_type: str
    reason: str
    violating_zone_id: Optional[str] = None  # set when the violation is a *neighboring* zone's reading
    severity: str = "warning"  # "warning" | "critical"


class PermitIntelligenceAgent:
    def __init__(self, blackboard: Blackboard, radius_hops: int = DEFAULT_RADIUS_HOPS,
                 caution_fraction: float = GAS_CAUTION_FRACTION):
        self.bb = blackboard
        self.radius_hops = radius_hops
        self.caution_fraction = caution_fraction

    def _gas_caution_level(self) -> float:
        return STATUTORY_THRESHOLDS["gas_ppm"] * self.caution_fraction

    def _check_hot_work_permit(self, permit: Permit) -> List[PermitViolation]:
        violations = []
        own_snap = self.bb.snapshot(permit.zone_id)
        gas_value = own_snap.sensor_value("gas_ppm")
        caution_level = self._gas_caution_level()

        if gas_value is not None and gas_value >= STATUTORY_THRESHOLDS["gas_ppm"]:
            violations.append(PermitViolation(
                permit_id=permit.permit_id, zone_id=permit.zone_id,
                permit_type=permit.permit_type,
                reason=f"gas reading {gas_value:.2f}ppm exceeds statutory threshold "
                       f"({STATUTORY_THRESHOLDS['gas_ppm']}ppm) in the permit's own zone",
                severity="critical",
            ))
        elif gas_value is not None and gas_value >= caution_level:
            violations.append(PermitViolation(
                permit_id=permit.permit_id, zone_id=permit.zone_id,
                permit_type=permit.permit_type,
                reason=f"gas reading {gas_value:.2f}ppm is at {gas_value / STATUTORY_THRESHOLDS['gas_ppm']:.0%} "
                       f"of statutory threshold in the permit's own zone",
                severity="warning",
            ))

        for neighbor_id in zones_within_radius(permit.zone_id, self.radius_hops):
            neighbor_snap = self.bb.snapshot(neighbor_id)
            neighbor_gas = neighbor_snap.sensor_value("gas_ppm")
            if neighbor_gas is not None and neighbor_gas >= caution_level:
                violations.append(PermitViolation(
                    permit_id=permit.permit_id, zone_id=permit.zone_id,
                    permit_type=permit.permit_type,
                    reason=f"elevated gas ({neighbor_gas:.2f}ppm) within {self.radius_hops} hop(s) "
                           f"in {neighbor_id}",
                    violating_zone_id=neighbor_id,
                    severity="warning",
                ))
        return violations

    def validate_on_issue(self, permit: Permit) -> List[PermitViolation]:
        if permit.permit_type != "hot_work":
            return []  # only hot-work has a gas-proximity rule for now
        return self._check_hot_work_permit(permit)

    def revalidate_all(self) -> List[PermitViolation]:
        violations = []
        for zone_id in self.bb.all_zone_ids():
            for permit in self.bb.graph.active_permits(zone_id):
                if permit.permit_type == "hot_work":
                    violations.extend(self._check_hot_work_permit(permit))
        return violations
