from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.middlewares.auth_middleware import get_current_user, require_role, verify_service_token
from app.models.base import get_db
from app.repositories.alert_repository import AlertRepository
from app.schemas.alert_schema import AlertConfirmResponse, AlertCreate, AlertResponse
from app.schemas.auth_schema import UserInToken
from app.services.notification_service import notification_service

router = APIRouter(prefix="/alerts")


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    zone_id: uuid.UUID | None = None,
    severity: str | None = None,
    current_user: Annotated[UserInToken, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """List active alerts, optionally filtered by zone or severity."""
    repo = AlertRepository(db)
    return await repo.list_active_alerts(zone_id=zone_id, severity=severity)


@router.get("/confirmed", response_model=list[AlertResponse])
async def list_confirmed_alerts(
    current_user: Annotated[UserInToken, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """List confirmed alerts."""
    repo = AlertRepository(db)
    return await repo.list_confirmed_alerts()

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: uuid.UUID,
    current_user: Annotated[UserInToken, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single alert with its full causal graph_path and evidence snapshot."""
    repo = AlertRepository(db)
    alert = await repo.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.patch("/{alert_id}/confirm", response_model=AlertConfirmResponse)
async def confirm_alert(
    alert_id: uuid.UUID,
    current_user: Annotated[UserInToken, Depends(require_role("plant_admin"))],
    db: AsyncSession = Depends(get_db),
):
    """Human-in-the-loop confirmation gate — plant_admin only.
    Creates an evidence snapshot and dispatches Twilio notification.
    """
    repo = AlertRepository(db)
    alert = await repo.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if alert.confirmed_by:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Alert already confirmed")

    user_id = uuid.UUID(current_user.user_id)
    confirmed = await repo.confirm_alert(alert_id, user_id)

    # Write immutable evidence snapshot
    await repo.create_evidence_snapshot(
        alert_id=alert_id,
        snapshot_data={
            "alert_id": str(alert_id),
            "severity": alert.severity,
            "graph_path": alert.graph_path,
            "confirmed_by": str(user_id),
            "confirmed_at": confirmed.confirmed_at.isoformat() if confirmed.confirmed_at else None,
        },
    )

    # Write audit log
    await repo.create_audit_log(
        user_id=user_id,
        action="evacuation_confirmed",
        resource_type="alert",
        resource_id=alert_id,
        details={"severity": alert.severity},
    )

    # Dispatch Twilio notification (fire-and-forget, errors are swallowed)
    import asyncio
    asyncio.create_task(
        notification_service.send_alert_notification(
            alert_id=str(alert_id),
            zone_name=str(alert.zone_id),
            severity=alert.severity,
            recipients=[],  # TODO: pull from zone/plant config
        )
    )

    return AlertConfirmResponse(
        id=confirmed.id,
        confirmed_by=user_id,
        confirmed_at=confirmed.confirmed_at or datetime.now(timezone.utc),
    )


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreate,
    _: None = Depends(verify_service_token),
    db: AsyncSession = Depends(get_db),
):
    """Internal: create an alert (called by agents/orchestrator via service token)."""
    repo = AlertRepository(db)
    alert = await repo.create_alert(
        {
            "zone_id": body.zone_id,
            "severity": body.severity,
            "title": body.title,
            "description": body.description,
            "graph_path": body.graph_path,
            "triggered_at": datetime.now(timezone.utc),
        }
    )
    return alert
