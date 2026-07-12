from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.middlewares.auth_middleware import verify_service_token
from app.services.ingestion_service import IngestionService
from app.utils.ingest_adapters import normalize_simulator_event

router = APIRouter(prefix="/events")


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    event: dict[str, Any],
    _: None = Depends(verify_service_token),
):
    """Generic ingest endpoint for permit, shift, and CV events from simulator/CV pipeline."""
    if "event_type" not in event:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="event_type is required")
    normalized = normalize_simulator_event(event)
    await IngestionService.publish_raw_event(normalized)
    return {"status": "accepted", "event_type": normalized["event_type"]}
