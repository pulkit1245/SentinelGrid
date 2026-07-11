"""
Zone definitions for the Synthetic Plant Simulator.

IMPORTANT: zone_id / zone_name here must be coordinated with Member 1's
seed script so the floor-plan overlay lines up exactly with simulated data.
If Member 1 changes an ID, update it here (single source of truth for M2).
"""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Zone:
    zone_id: str
    zone_name: str
    hazard_classes: List[str]
    # baseline "resting" readings + noise sigma per sensor type
    baseline: dict = field(default_factory=dict)


# 6 zones covering a plausible industrial-plant footprint.
# hazard_classes drive which sensor types get generated for that zone
# and which agent rules can even fire there (e.g. only zones with
# "flammable_gas" can trigger the hot-work compound-risk pattern).
ZONES: List[Zone] = [
    Zone(
        zone_id="zone-01-degassing",
        zone_name="Degassing Bay",
        hazard_classes=["flammable_gas", "hot_work_permitted"],
        baseline={"gas_ppm": (8.0, 1.2), "temp_c": (34.0, 1.5),
                   "pressure_kpa": (101.3, 0.4), "vibration_mm_s": (1.1, 0.2)},
    ),
    Zone(
        zone_id="zone-02-castfloor",
        zone_name="Cast Floor",
        hazard_classes=["high_temp", "heavy_machinery"],
        baseline={"gas_ppm": (2.0, 0.5), "temp_c": (55.0, 3.0),
                   "pressure_kpa": (101.3, 0.3), "vibration_mm_s": (3.2, 0.6)},
    ),
    Zone(
        zone_id="zone-03-tankfarm",
        zone_name="Tank Farm",
        hazard_classes=["flammable_gas", "pressure_vessel"],
        baseline={"gas_ppm": (5.0, 1.0), "temp_c": (28.0, 1.0),
                   "pressure_kpa": (250.0, 4.0), "vibration_mm_s": (0.6, 0.15)},
    ),
    Zone(
        zone_id="zone-04-loadingdock",
        zone_name="Loading Dock",
        hazard_classes=["vehicle_traffic", "hot_work_permitted"],
        baseline={"gas_ppm": (3.0, 0.8), "temp_c": (26.0, 2.0),
                   "pressure_kpa": (101.3, 0.3), "vibration_mm_s": (1.8, 0.4)},
    ),
    Zone(
        zone_id="zone-05-compressor",
        zone_name="Compressor House",
        hazard_classes=["high_temp", "pressure_vessel", "high_noise"],
        baseline={"gas_ppm": (1.5, 0.4), "temp_c": (42.0, 2.0),
                   "pressure_kpa": (310.0, 6.0), "vibration_mm_s": (4.5, 0.8)},
    ),
    Zone(
        zone_id="zone-06-control",
        zone_name="Control Room",
        hazard_classes=[],
        baseline={"gas_ppm": (0.5, 0.1), "temp_c": (22.0, 0.5),
                   "pressure_kpa": (101.3, 0.1), "vibration_mm_s": (0.1, 0.05)},
    ),
]

ZONE_BY_ID = {z.zone_id: z for z in ZONES}

# Statutory single-sensor thresholds (used by baseline_comparator.py and
# as the non-overridable hard-rules floor referenced by the Orchestrator).
STATUTORY_THRESHOLDS = {
    "gas_ppm": 25.0,       # e.g. LEL-fraction proxy
    "temp_c": 80.0,
    "pressure_kpa": 400.0,
    "vibration_mm_s": 7.1,  # ISO 10816-esque "danger" band proxy
}

# Simple adjacency graph (hop-distance stand-in for a physical "radius" --
# no floor-plan coordinates exist yet, so the Permit Intelligence Agent's
# "hot work within a configurable radius of elevated gas readings" check
# uses hop-count over this adjacency instead of literal meters). Update
# this once Member 1's floor-plan overlay defines real coordinates.
ZONE_ADJACENCY = {
    "zone-01-degassing": ["zone-02-castfloor", "zone-03-tankfarm"],
    "zone-02-castfloor": ["zone-01-degassing", "zone-04-loadingdock"],
    "zone-03-tankfarm": ["zone-01-degassing", "zone-05-compressor"],
    "zone-04-loadingdock": ["zone-02-castfloor", "zone-06-control"],
    "zone-05-compressor": ["zone-03-tankfarm", "zone-06-control"],
    "zone-06-control": ["zone-04-loadingdock", "zone-05-compressor"],
}


def zones_within_radius(zone_id: str, radius_hops: int = 1) -> List[str]:
    """BFS over ZONE_ADJACENCY; returns zone_ids within `radius_hops` hops (excludes zone_id itself)."""
    visited = {zone_id}
    frontier = [zone_id]
    result = []
    for _ in range(radius_hops):
        next_frontier = []
        for z in frontier:
            for neighbor in ZONE_ADJACENCY.get(z, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    result.append(neighbor)
                    next_frontier.append(neighbor)
        frontier = next_frontier
    return result
