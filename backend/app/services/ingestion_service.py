from __future__ import annotations

import json
import logging
from datetime import datetime

import redis.asyncio as aioredis

from app.core.config import settings
from app.repositories.sensor_repository import SensorRepository
from app.schemas.sensor_schema import SensorIngestRequest

logger = logging.getLogger(__name__)

SENSOR_STREAM_KEY = "sentinelgrid:sensor_readings"
PERMIT_STREAM_KEY = "sentinelgrid:permit_events"


async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


class IngestionService:
    def __init__(self, sensor_repo: SensorRepository) -> None:
        self.sensor_repo = sensor_repo

    async def ingest_sensor_reading(self, payload: SensorIngestRequest) -> dict:
        """Validate, persist, and stream a sensor reading."""
        # 1. Verify sensor exists
        sensor = await self.sensor_repo.get_sensor(payload.sensor_id)
        if not sensor:
            raise ValueError(f"Sensor {payload.sensor_id} not found")

        # 2. Write to TimescaleDB
        reading = await self.sensor_repo.create_sensor_reading(
            sensor_id=payload.sensor_id,
            zone_id=payload.zone_id,
            value=payload.value,
            recorded_at=payload.recorded_at,
        )

        # 3. Publish to Redis Stream for enrichment worker
        await self._publish_to_stream(
            SENSOR_STREAM_KEY,
            {
                "sensor_id": str(payload.sensor_id),
                "zone_id": str(payload.zone_id),
                "sensor_type": payload.sensor_type,
                "value": str(payload.value),
                "unit": payload.unit,
                "recorded_at": payload.recorded_at.isoformat(),
            },
        )

        logger.info(
            "Sensor reading ingested",
            extra={"sensor_id": str(payload.sensor_id), "value": payload.value},
        )
        return {"reading_id": str(reading.id), "status": "ingested"}

    async def publish_permit_event(self, event_data: dict) -> None:
        """Publish a permit lifecycle event to the Redis Stream."""
        await self._publish_to_stream(PERMIT_STREAM_KEY, event_data)

    async def _publish_to_stream(self, stream_key: str, data: dict) -> None:
        try:
            r = await get_redis()
            await r.xadd(stream_key, data, maxlen=10_000, approximate=True)
            await r.aclose()
        except Exception as exc:
            logger.warning("Failed to publish to Redis stream", extra={"error": str(exc)})
