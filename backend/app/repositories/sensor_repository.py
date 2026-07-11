from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading


class SensorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_sensor(self, sensor_id: uuid.UUID) -> Sensor | None:
        result = await self.session.execute(select(Sensor).where(Sensor.id == sensor_id))
        return result.scalar_one_or_none()

    async def list_sensors_for_zone(self, zone_id: uuid.UUID) -> Sequence[Sensor]:
        result = await self.session.execute(select(Sensor).where(Sensor.zone_id == zone_id))
        return result.scalars().all()

    async def create_sensor_reading(
        self,
        sensor_id: uuid.UUID,
        zone_id: uuid.UUID,
        value: float,
        recorded_at: datetime,
    ) -> SensorReading:
        reading = SensorReading(
            sensor_id=sensor_id,
            zone_id=zone_id,
            reading_value=value,
            recorded_at=recorded_at,
        )
        self.session.add(reading)
        await self.session.flush()
        return reading

    async def get_recent_readings(
        self, sensor_id: uuid.UUID, limit: int = 100
    ) -> Sequence[SensorReading]:
        result = await self.session.execute(
            select(SensorReading)
            .where(SensorReading.sensor_id == sensor_id)
            .order_by(SensorReading.recorded_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
