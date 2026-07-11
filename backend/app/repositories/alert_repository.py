from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.evidence_snapshot import EvidenceSnapshot


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_alert(self, data: dict) -> Alert:
        alert = Alert(**data)
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def get_alert(self, alert_id: uuid.UUID) -> Alert | None:
        result = await self.session.execute(select(Alert).where(Alert.id == alert_id))
        return result.scalar_one_or_none()

    async def list_active_alerts(
        self,
        zone_id: uuid.UUID | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> Sequence[Alert]:
        stmt = select(Alert).where(Alert.is_active == True)
        if zone_id:
            stmt = stmt.where(Alert.zone_id == zone_id)
        if severity:
            stmt = stmt.where(Alert.severity == severity)
        stmt = stmt.order_by(Alert.triggered_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    async def list_confirmed_alerts(self, limit: int = 50) -> Sequence[Alert]:
        stmt = select(Alert).where(Alert.confirmed_by.is_not(None)).order_by(Alert.confirmed_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    async def confirm_alert(self, alert_id: uuid.UUID, user_id: uuid.UUID) -> Alert | None:
        confirmed_at = datetime.now(timezone.utc)
        await self.session.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .values(confirmed_by=user_id, confirmed_at=confirmed_at)
        )
        await self.session.flush()
        return await self.get_alert(alert_id)

    async def create_evidence_snapshot(
        self, alert_id: uuid.UUID, snapshot_data: dict, s3_key: str | None = None
    ) -> EvidenceSnapshot:
        snapshot = EvidenceSnapshot(
            alert_id=alert_id,
            snapshot_data=snapshot_data,
            s3_key=s3_key,
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_evidence_snapshot(self, alert_id: uuid.UUID) -> EvidenceSnapshot | None:
        result = await self.session.execute(
            select(EvidenceSnapshot).where(EvidenceSnapshot.alert_id == alert_id)
        )
        return result.scalar_one_or_none()

    async def create_audit_log(
        self,
        user_id: uuid.UUID | None,
        action: str,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
        self.session.add(log)
        await self.session.flush()
        return log
