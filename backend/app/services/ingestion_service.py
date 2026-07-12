from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.ingest_queue import publish_ingest_event
from app.repositories.sensor_repository import SensorRepository
from app.schemas.sensor_schema import SensorIngestRequest

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, sensor_repo: SensorRepository) -> None:
        self.sensor_repo = sensor_repo

    @staticmethod
    async def publish_raw_event(event: dict) -> None:
        """Publish a normalized event to the enrichment worker queue."""
        try:
            await publish_ingest_event(event)
        except Exception as exc:
            logger.warning("Failed to publish ingest event", extra={"error": str(exc)})

    async def ingest_sensor_reading(self, payload: SensorIngestRequest) -> dict:
        """Validate, persist, and stream a sensor reading."""
        sensor = await self.sensor_repo.get_sensor(payload.sensor_id)
        if not sensor:
            raise ValueError(f"Sensor {payload.sensor_id} not found")
        if str(sensor.zone_id) != str(payload.zone_id):
            raise ValueError(f"zone_id {payload.zone_id} does not match sensor's zone {sensor.zone_id}")

        reading = await self.sensor_repo.create_sensor_reading(
            sensor_id=payload.sensor_id,
            zone_id=payload.zone_id,
            value=payload.value,
            recorded_at=payload.recorded_at,
        )

        recorded_at = payload.recorded_at
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)

        event = {
            "event_type": "sensor_reading",
            "sensor_id": str(payload.sensor_id),
            "zone_id": str(payload.zone_id),
            "sensor_type": payload.sensor_type,
            "value": payload.value,
            "unit": payload.unit,
            "recorded_at": recorded_at.isoformat(),
            "sim_time_s": recorded_at.timestamp(),
        }
        await self.publish_raw_event(event)

        logger.info(
            "Sensor reading ingested",
            extra={"sensor_id": str(payload.sensor_id), "value": payload.value},
        )
        return {"reading_id": str(reading.id), "status": "ingested"}

    async def publish_permit_event(self, event_data: dict) -> None:
        """Publish a permit lifecycle event to the enrichment queue."""
        if "event_type" not in event_data:
            event_data = {**event_data, "event_type": "permit_created"}
        await self.publish_raw_event(event_data)
