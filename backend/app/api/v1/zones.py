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


DEFAULT_DEMO_ZONES = [
    ZoneResponse(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        plant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="Zone 1 – Degassing & Separator",
        hazard_class="gas",
        current_risk_score=78,
        active_permit_count=1,
        active_alert_count=1,
        slug="zone-01-degassing",
    ),
    ZoneResponse(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        plant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="Zone 2 – Gas Compression Bay",
        hazard_class="gas",
        current_risk_score=42,
        active_permit_count=0,
        active_alert_count=0,
        slug="zone-02-compressor",
    ),
    ZoneResponse(
        id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        plant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="Zone 3 – Liquid Fuel Storage",
        hazard_class="thermal",
        current_risk_score=15,
        active_permit_count=1,
        active_alert_count=0,
        slug="zone-03-storage",
    ),
    ZoneResponse(
        id=uuid.UUID("00000000-0000-0000-0000-000000000004"),
        plant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="Zone 4 – Flare Stack & Header",
        hazard_class="thermal",
        current_risk_score=85,
        active_permit_count=2,
        active_alert_count=1,
        slug="zone-04-flare",
    ),
]


@router.get("", response_model=ZoneList)
async def list_zones(
    current_user: Annotated[UserInToken, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """List all zones with current risk score and permit/alert counts."""
    try:
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

        if result:
            return ZoneList(zones=result, total=len(result))
    except Exception:
        pass

    return ZoneList(zones=DEFAULT_DEMO_ZONES, total=len(DEFAULT_DEMO_ZONES))


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: str,
    current_user: Annotated[UserInToken, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get a single zone with full detail."""
    try:
        z_uuid = uuid.UUID(zone_id)
        zone_repo = ZoneRepository(db)
        zone = await zone_repo.get_zone(z_uuid)
        if zone:
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
    except Exception:
        pass

    for dz in DEFAULT_DEMO_ZONES:
        if str(dz.id) == zone_id or dz.slug == zone_id:
            return dz

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")


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


# ── Black Box & Agent Transcript Endpoints ────────────────────────────────────

@router.get("/{zone_id}/black-box")
async def get_black_box_timeline(zone_id: str):
    """Full historical timeline entries for a zone from BlackBoxRecorder."""
    from app.core.orchestrator_manager import orchestrator_manager
    return orchestrator_manager.get_black_box_timeline(zone_id)


@router.get("/{zone_id}/black-box/changes")
async def get_black_box_story_beats(zone_id: str):
    """Moments when decision changed ('story beats') for a zone."""
    from app.core.orchestrator_manager import orchestrator_manager
    return orchestrator_manager.get_black_box_story_beats(zone_id)


@router.get("/{zone_id}/transcript")
async def get_agent_transcript(zone_id: str, sim_time_s: float | None = None):
    """Agent debate transcript for a zone at current state or specific sim_time_s."""
    from app.core.orchestrator_manager import orchestrator_manager
    return orchestrator_manager.get_agent_transcript(zone_id, sim_time_s=sim_time_s)


@router.post("/{zone_id}/black-box/simulate")
async def simulate_black_box_scenario(zone_id: str):
    """Trigger a scenario simulation run to generate live black box events."""
    from app.core.orchestrator_manager import orchestrator_manager
    orchestrator_manager.seed_default_scenario(target_zone=zone_id)
    return {
        "status": "success",
        "zone_id": zone_id,
        "entry_count": len(orchestrator_manager.black_box.timeline_for_zone(zone_id)),
        "story_beat_count": len(orchestrator_manager.black_box.decision_changes(zone_id)),
    }

