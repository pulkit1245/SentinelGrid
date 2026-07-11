from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.middlewares.auth_middleware import get_current_user
from app.schemas.auth_schema import UserInToken

router = APIRouter(prefix="/graph")


@router.get("/zones/{zone_id}")
async def get_zone_graph(
    zone_id: uuid.UUID,
    current_user: Annotated[UserInToken, Depends(get_current_user)],
):
    """Return graph data for a zone — nodes and edges from the Plant Risk Graph.

    NOTE: Full implementation is owned by Member 3 (graph_builder.py / pattern_queries.py).
    This stub returns a placeholder so the frontend graph visualisation can render.
    """
    # TODO(Member 3): wire to graph_client.get_zone_subgraph(zone_id)
    return {
        "zone_id": str(zone_id),
        "nodes": [
            {"id": str(zone_id), "type": "Zone", "label": "Zone"},
        ],
        "edges": [],
        "note": "Full graph data available once Member 3's graph module is integrated.",
    }
