from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.tests.conftest import get_auth_token
from app.models.user import User


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, safety_officer_user: User):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "officer@sentinelgrid.test", "password": "password123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, safety_officer_user: User):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "officer@sentinelgrid.test", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@sentinelgrid.test", "password": "password123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/zones")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/api/v1/zones",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_valid_token(client: AsyncClient, safety_officer_user: User):
    token = await get_auth_token(client, "officer@sentinelgrid.test")
    resp = await client.get(
        "/api/v1/zones",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should succeed (even if no zones exist yet)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_role_mismatch_on_admin_endpoint(client: AsyncClient, safety_officer_user: User):
    """safety_officer should not be able to access plant_admin-only routes."""
    token = await get_auth_token(client, "officer@sentinelgrid.test")
    # Try to confirm an alert (plant_admin only) — should get 403
    import uuid
    resp = await client.patch(
        f"/api/v1/alerts/{uuid.uuid4()}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
