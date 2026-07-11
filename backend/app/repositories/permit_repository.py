from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permit import Permit


class PermitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_permit(self, data: dict) -> Permit:
        permit = Permit(**data)
        self.session.add(permit)
        await self.session.flush()
        return permit

    async def get_permit(self, permit_id: uuid.UUID) -> Permit | None:
        result = await self.session.execute(select(Permit).where(Permit.id == permit_id))
        return result.scalar_one_or_none()

    async def get_active_permits_for_zone(self, zone_id: uuid.UUID) -> Sequence[Permit]:
        result = await self.session.execute(
            select(Permit).where(
                and_(Permit.zone_id == zone_id, Permit.status == "active")
            )
        )
        return result.scalars().all()

    async def get_conflicting_permits(
        self,
        zone_id: uuid.UUID,
        permit_type: str,
        valid_from: datetime,
        valid_to: datetime,
    ) -> Sequence[Permit]:
        """Find active permits of the same type in the same zone that overlap in time."""
        result = await self.session.execute(
            select(Permit).where(
                and_(
                    Permit.zone_id == zone_id,
                    Permit.permit_type == permit_type,
                    Permit.status == "active",
                    Permit.valid_from < valid_to,
                    Permit.valid_to > valid_from,
                )
            )
        )
        return result.scalars().all()

    async def update_permit_status(self, permit_id: uuid.UUID, status: str) -> Permit | None:
        await self.session.execute(
            update(Permit).where(Permit.id == permit_id).values(status=status)
        )
        await self.session.flush()
        return await self.get_permit(permit_id)

    async def list_permits_for_zone(self, zone_id: uuid.UUID) -> Sequence[Permit]:
        result = await self.session.execute(
            select(Permit)
            .where(Permit.zone_id == zone_id)
            .order_by(Permit.valid_from.desc())
        )
        return result.scalars().all()
