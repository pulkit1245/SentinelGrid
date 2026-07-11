from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone import Zone
from app.models.worker import Worker
from app.models.user import User
from app.tests.conftest import get_auth_token


def future_window():
    now = datetime.now(timezone.utc)
    return now + timedelta(hours=1), now + timedelta(hours=8)


@pytest.mark.asyncio
async def test_create_permit(client: AsyncClient, safety_officer_user: User, db_session: AsyncSession):
    zone = Zone(id=uuid.uuid4(), plant_id=uuid.uuid4(), name="Permit Test Zone", hazard_class="gas", current_risk_score=0)
    db_session.add(zone)
    await db_session.commit()

    token = await get_auth_token(client, "officer@sentinelgrid.test")
    valid_from, valid_to = future_window()

    resp = await client.post(
        "/api/v1/permits",
        json={
            "zone_id": str(zone.id),
            "permit_type": "hot_work",
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["permit_type"] == "hot_work"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_permit_conflict(client: AsyncClient, safety_officer_user: User, db_session: AsyncSession):
    zone = Zone(id=uuid.uuid4(), plant_id=uuid.uuid4(), name="Conflict Zone", hazard_class="gas", current_risk_score=0)
    db_session.add(zone)
    await db_session.commit()

    token = await get_auth_token(client, "officer@sentinelgrid.test")
    valid_from, valid_to = future_window()

    payload = {
        "zone_id": str(zone.id),
        "permit_type": "hot_work",
        "valid_from": valid_from.isoformat(),
        "valid_to": valid_to.isoformat(),
    }

    resp1 = await client.post("/api/v1/permits", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp1.status_code == 201

    # Second overlapping permit of same type should 409
    resp2 = await client.post("/api/v1/permits", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_get_permit_not_found(client: AsyncClient, safety_officer_user: User):
    token = await get_auth_token(client, "officer@sentinelgrid.test")
    resp = await client.get(
        f"/api/v1/permits/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
