from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone import Zone


class ZoneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_zones(self, plant_id: uuid.UUID | None = None) -> Sequence[Zone]:
        stmt = select(Zone)
        if plant_id:
            stmt = stmt.where(Zone.plant_id == plant_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_zone(self, zone_id: uuid.UUID) -> Zone | None:
        result = await self.session.execute(select(Zone).where(Zone.id == zone_id))
        return result.scalar_one_or_none()

    async def create_zone(self, data: dict) -> Zone:
        zone = Zone(**data)
        self.session.add(zone)
        await self.session.flush()
        return zone

    async def update_zone_risk_score(self, zone_id: uuid.UUID, score: int) -> Zone | None:
        await self.session.execute(
            update(Zone).where(Zone.id == zone_id).values(current_risk_score=score)
        )
        await self.session.flush()
        return await self.get_zone(zone_id)
