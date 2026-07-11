from __future__ import annotations

import uuid
from datetime import datetime

from app.repositories.permit_repository import PermitRepository


class PermitValidationService:
    """Validates permits for conflicts before issuance."""

    def __init__(self, permit_repo: PermitRepository) -> None:
        self.permit_repo = permit_repo

    async def check_permit_conflicts(
        self,
        zone_id: uuid.UUID,
        permit_type: str,
        valid_from: datetime,
        valid_to: datetime,
    ) -> list[dict]:
        """Return a list of conflicting active permits, empty if none."""
        conflicts = await self.permit_repo.get_conflicting_permits(
            zone_id=zone_id,
            permit_type=permit_type,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        return [
            {
                "permit_id": str(p.id),
                "permit_type": p.permit_type,
                "valid_from": p.valid_from.isoformat(),
                "valid_to": p.valid_to.isoformat(),
                "status": p.status,
            }
            for p in conflicts
        ]
