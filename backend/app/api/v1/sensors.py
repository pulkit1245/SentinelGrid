from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.middlewares.auth_middleware import get_current_user, verify_service_token
from app.models.base import get_db
from app.repositories.sensor_repository import SensorRepository
from app.schemas.auth_schema import UserInToken
from app.schemas.sensor_schema import SensorIngestRequest, SensorReadingResponse, SensorResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/sensors")


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_sensor_reading(
    body: SensorIngestRequest,
    _: None = Depends(verify_service_token),
    db: AsyncSession = Depends(get_db),
):
    """Service-token-authenticated ingestion endpoint for simulator/adapter layer.
    Validates against shared schema, writes to TimescaleDB, publishes to Redis Stream.
    """
    sensor_repo = SensorRepository(db)
    service = IngestionService(sensor_repo)
    try:
        result = await service.ingest_sensor_reading(body)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{sensor_id}", response_model=SensorResponse)
async def get_sensor(
    sensor_id: uuid.UUID,
    current_user: Annotated[UserInToken, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get sensor metadata."""
    repo = SensorRepository(db)
    sensor = await repo.get_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return sensor


@router.get("/{sensor_id}/readings", response_model=list[SensorReadingResponse])
async def get_sensor_readings(
    sensor_id: uuid.UUID,
    limit: int = 100,
    current_user: Annotated[UserInToken, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get recent readings for a sensor."""
    repo = SensorRepository(db)
    readings = await repo.get_recent_readings(sensor_id, limit=limit)
    return readings
