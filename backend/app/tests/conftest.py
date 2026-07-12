from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator

import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_password_hash
from app.main import app
from app.models.base import Base, get_db
from app.models.user import User

# ── Test Database ─────────────────────────────────────────────────────────────
TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://sentinelgrid:password@localhost:5432/sentinelgrid_test",
)

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def safety_officer_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="officer@sentinelgrid.test",
        password_hash=get_password_hash("password123"),
        role="safety_officer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def plant_admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@sentinelgrid.test",
        password_hash=get_password_hash("password123"),
        role="plant_admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def get_auth_token(client: AsyncClient, email: str, password: str = "password123") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]
