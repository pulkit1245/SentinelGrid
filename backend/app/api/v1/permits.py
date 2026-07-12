from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.middlewares.auth_middleware import get_current_user, require_role
from app.models.base import get_db
from app.repositories.permit_repository import PermitRepository
from app.schemas.auth_schema import UserInToken
from app.schemas.permit_schema import PermitCreate, PermitResponse
from app.services.ingestion_service import IngestionService
from app.services.permit_validation_service import PermitValidationService

router = APIRouter(prefix="/permits")


@router.post("", response_model=PermitResponse, status_code=status.HTTP_201_CREATED)
async def create_permit(
    body: PermitCreate,
    current_user: Annotated[UserInToken, Depends(require_role("safety_officer", "plant_admin"))],
    db: AsyncSession = Depends(get_db),
):
    """Issue a new permit-to-work, checking for conflicting active permits (409 on conflict)."""
    permit_repo = PermitRepository(db)
    validation_service = PermitValidationService(permit_repo)

    conflicts = await validation_service.check_permit_conflicts(
        zone_id=body.zone_id,
        permit_type=body.permit_type,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
    )

    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Conflicting active permit exists", "conflicts": conflicts},
        )

    permit = await permit_repo.create_permit(
        {
            "zone_id": body.zone_id,
            "permit_type": body.permit_type,
            "issued_to_worker_id": body.issued_to_worker_id,
            "issued_by_user_id": uuid.UUID(current_user.user_id),
            "valid_from": body.valid_from,
            "valid_to": body.valid_to,
            "notes": body.notes,
            "status": "active",
        }
    )

    await IngestionService.publish_raw_event(
        {
            "event_type": "permit_issued",
            "permit_id": str(permit.id),
            "zone_id": str(permit.zone_id),
            "permit_type": permit.permit_type,
            "sim_time_s": permit.valid_from.timestamp(),
        }
    )

    from app.api.v1.dashboard_ws import broadcast_event

    await broadcast_event(
        "permit_created",
        {
            "id": str(permit.id),
            "zone_id": str(permit.zone_id),
            "permit_type": permit.permit_type,
            "status": permit.status,
            "valid_from": permit.valid_from.isoformat(),
            "valid_to": permit.valid_to.isoformat(),
        },
    )
    return permit


@router.get("/{permit_id}", response_model=PermitResponse)
async def get_permit(
    permit_id: uuid.UUID,
    current_user: Annotated[UserInToken, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get permit details."""
    repo = PermitRepository(db)
    permit = await repo.get_permit(permit_id)
    if not permit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permit not found")
    return permit


@router.patch("/{permit_id}/revoke", response_model=PermitResponse)
async def revoke_permit(
    permit_id: uuid.UUID,
    current_user: Annotated[UserInToken, Depends(require_role("plant_admin"))],
    db: AsyncSession = Depends(get_db),
):
    """Revoke an active permit. Restricted to plant_admin."""
    repo = PermitRepository(db)
    permit = await repo.get_permit(permit_id)
    if not permit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permit not found")
    if permit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Permit is not active")
    updated = await repo.update_permit_status(permit_id, "revoked")

    await IngestionService.publish_raw_event(
        {
            "event_type": "permit_closed",
            "permit_id": str(permit_id),
            "zone_id": str(permit.zone_id),
            "sim_time_s": 0,
        }
    )

    from app.api.v1.dashboard_ws import broadcast_event

    await broadcast_event(
        "permit_revoked",
        {"id": str(permit_id), "zone_id": str(permit.zone_id), "status": "revoked"},
    )
    return updated


@router.get("/zone/{zone_id}", response_model=list[PermitResponse])
async def list_zone_permits(
    zone_id: uuid.UUID,
    current_user: Annotated[UserInToken, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """List all permits (active and historical) for a zone."""
    repo = PermitRepository(db)
    return await repo.list_permits_for_zone(zone_id)
