from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.middlewares.auth_middleware import get_current_user, require_role, verify_service_token
from app.models.base import get_db
from app.repositories.alert_repository import AlertRepository
from app.repositories.permit_repository import PermitRepository
from app.repositories.zone_repository import ZoneRepository
from app.schemas.auth_schema import UserInToken
from app.schemas.zone_schema import ZoneList, ZoneResponse, ZoneRiskUpdate

router = APIRouter(prefix="/zones")


@router.get("", response_model=ZoneList)
async def list_zones(
    current_user: Annotated[UserInToken, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """List all zones with current risk score and permit/alert counts."""
    zone_repo = ZoneRepository(db)
    permit_repo = PermitRepository(db)
    alert_repo = AlertRepository(db)

    plant_id = uuid.UUID(current_user.plant_id) if current_user.plant_id else None
    zones = await zone_repo.list_zones(plant_id=plant_id)

    result = []
    for zone in zones:
        active_permits = await permit_repo.get_active_permits_for_zone(zone.id)
        active_alerts = await alert_repo.list_active_alerts(zone_id=zone.id)
        result.append(
            ZoneResponse(
                id=zone.id,
                plant_id=zone.plant_id,
                name=zone.name,
                hazard_class=zone.hazard_class,
                polygon_geojson=zone.polygon_geojson,
                current_risk_score=zone.current_risk_score,
                active_permit_count=len(active_permits),
                active_alert_count=len(active_alerts),
                slug=zone.slug,
            )
        )

    return ZoneList(zones=result, total=len(result))


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: uuid.UUID,
    current_user: Annotated[UserInToken, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get a single zone with full detail."""
    zone_repo = ZoneRepository(db)
    zone = await zone_repo.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    permit_repo = PermitRepository(db)
    alert_repo = AlertRepository(db)
    active_permits = await permit_repo.get_active_permits_for_zone(zone.id)
    active_alerts = await alert_repo.list_active_alerts(zone_id=zone.id)

    return ZoneResponse(
        id=zone.id,
        plant_id=zone.plant_id,
        name=zone.name,
        hazard_class=zone.hazard_class,
        polygon_geojson=zone.polygon_geojson,
        current_risk_score=zone.current_risk_score,
        active_permit_count=len(active_permits),
        active_alert_count=len(active_alerts),
        slug=zone.slug,
    )


@router.patch("/{zone_id}/risk-score")
async def update_risk_score(
    zone_id: uuid.UUID,
    body: ZoneRiskUpdate,
    _: None = Depends(verify_service_token),
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint: update a zone's risk score (called by the scoring worker)."""
    zone_repo = ZoneRepository(db)
    zone = await zone_repo.update_zone_risk_score(zone_id, body.risk_score)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return {"zone_id": str(zone_id), "risk_score": body.risk_score}
