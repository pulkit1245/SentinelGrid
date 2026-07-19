"""
graph.py — stub route for zone causal graph path.
Returns a mock graph payload for the MVP cockpit dashboard.
"""
from fastapi import APIRouter, HTTPException, Path

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get("/zone/{zone_id}/path")
async def get_visual_lineage(zone_id: str = Path(..., title="The UUID of the zone")):
    """
    Returns causal graph data (nodes + edges) for an active alert in a zone.
    MVP stub: returns a sample graph structure.
    """
    # Minimal stub — replace with real Neo4j / networkx call in production
    return {
        "status": "success",
        "data": {
            "zone_id": zone_id,
            "nodes": [
                {"id": zone_id, "label": "Zone", "type": "zone"},
                {"id": f"sensor-{zone_id}-1", "label": "Gas Sensor", "type": "sensor"},
                {"id": f"worker-{zone_id}-1", "label": "Shift Worker", "type": "worker"},
            ],
            "edges": [
                {"source": f"sensor-{zone_id}-1", "target": zone_id, "label": "feeds"},
                {"source": f"worker-{zone_id}-1", "target": zone_id, "label": "assigned"},
            ],
        },
    }

