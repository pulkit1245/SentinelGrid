from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any

# We need to import from our networkx fallback for the hackathon MVP
from graph.networkx_fallback import fallback_graph

router = APIRouter(prefix="/graph", tags=["Graph"])

@router.get("/zone/{zone_id}/path")
async def get_visual_lineage(zone_id: str = Path(..., title="The UUID of the zone")):
    """
    Extracts the overlapping nodes (Permit, Sensor, Shift, Worker) responsible for an active alert.
    Transforms raw graph sub-networks into readable JSON payloads for the frontend cockpit dashboard.
    """
    try:
        # Query the networkx fallback client for the path around this zone
        payload = fallback_graph.get_path_for_alert(zone_id)
        
        if not payload or not payload.get("nodes"):
            raise HTTPException(status_code=404, detail="Zone not found in graph or has no relationships.")
            
        return {
            "status": "success",
            "data": payload
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
