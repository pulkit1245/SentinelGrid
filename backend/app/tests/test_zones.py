from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone import Zone
from app.models.user import User
from app.tests.conftest import get_auth_token


@pytest_asyncio_fixture_helper = None  # just a marker comment


@pytest.mark.asyncio
async def test_list_zones_empty(client: AsyncClient, safety_officer_user: User):
    token = await get_auth_token(client, "officer@sentinelgrid.test")
    resp = await client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "zones" in data
    assert isinstance(data["zones"], list)


@pytest.mark.asyncio
async def test_get_zone_not_found(client: AsyncClient, safety_officer_user: User):
    token = await get_auth_token(client, "officer@sentinelgrid.test")
    resp = await client.get(
        f"/api/v1/zones/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_risk_score_missing_service_token(client: AsyncClient):
    resp = await client.patch(
        f"/api/v1/zones/{uuid.uuid4()}/risk-score",
        json={"risk_score": 75},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_risk_score_with_service_token(client: AsyncClient, db_session: AsyncSession):
    # Insert a test zone
    zone = Zone(
        id=uuid.uuid4(),
        plant_id=uuid.uuid4(),
        name="Test Zone A",
        hazard_class="gas",
        current_risk_score=0,
    )
    db_session.add(zone)
    await db_session.commit()

    from app.core.config import settings
    resp = await client.patch(
        f"/api/v1/zones/{zone.id}/risk-score",
        json={"risk_score": 85},
        headers={"X-Service-Token": settings.SERVICE_TOKEN},
    )
    assert resp.status_code == 200
    assert resp.json()["risk_score"] == 85
