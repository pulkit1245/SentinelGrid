from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.zone import Zone
from app.models.user import User
from app.tests.conftest import get_auth_token
from app.core.config import settings


async def _create_test_alert(db_session: AsyncSession, zone_id: uuid.UUID) -> Alert:
    alert = Alert(
        id=uuid.uuid4(),
        zone_id=zone_id,
        severity="critical",
        title="Test Compound Risk Alert",
        description="Hot-work + gas trend",
        graph_path=[{"node": "Permit:hot_work", "rel": "OVERLAPS_WITH", "next": "Zone"}],
        triggered_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db_session.add(alert)
    await db_session.commit()
    return alert


@pytest.mark.asyncio
async def test_list_alerts(client: AsyncClient, safety_officer_user: User):
    token = await get_auth_token(client, "officer@sentinelgrid.test")
    resp = await client.get("/api/v1/alerts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_alert_not_found(client: AsyncClient, safety_officer_user: User):
    token = await get_auth_token(client, "officer@sentinelgrid.test")
    resp = await client.get(
        f"/api/v1/alerts/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_alert_via_service_token(client: AsyncClient, db_session: AsyncSession):
    zone = Zone(id=uuid.uuid4(), plant_id=uuid.uuid4(), name="Alert Test Zone", hazard_class="gas", current_risk_score=50)
    db_session.add(zone)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/alerts",
        json={
            "zone_id": str(zone.id),
            "severity": "warning",
            "title": "Test Alert",
            "graph_path": [],
        },
        headers={"X-Service-Token": settings.SERVICE_TOKEN},
    )
    assert resp.status_code == 201
    assert resp.json()["severity"] == "warning"


@pytest.mark.asyncio
async def test_confirm_alert_requires_plant_admin(client: AsyncClient, safety_officer_user: User, db_session: AsyncSession):
    """safety_officer should receive 403 on confirm."""
    zone = Zone(id=uuid.uuid4(), plant_id=uuid.uuid4(), name="Confirm Zone", hazard_class="thermal", current_risk_score=80)
    db_session.add(zone)
    await db_session.commit()

    alert = await _create_test_alert(db_session, zone.id)
    token = await get_auth_token(client, "officer@sentinelgrid.test")

    resp = await client.patch(
        f"/api/v1/alerts/{alert.id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_confirm_alert_as_plant_admin(client: AsyncClient, plant_admin_user: User, db_session: AsyncSession):
    zone = Zone(id=uuid.uuid4(), plant_id=uuid.uuid4(), name="Admin Confirm Zone", hazard_class="gas", current_risk_score=90)
    db_session.add(zone)
    await db_session.commit()

    alert = await _create_test_alert(db_session, zone.id)
    token = await get_auth_token(client, "admin@sentinelgrid.test")

    resp = await client.patch(
        f"/api/v1/alerts/{alert.id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "confirmed_by" in data
