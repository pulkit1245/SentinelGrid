#!/usr/bin/env python3
"""Seed script — populates the demo database with zones, sensors, workers, and users.

Run with:
    DATABASE_SYNC_URL=postgresql://... python -m scripts.seed_demo_data

Zone IDs are stable UUIDs so the simulator (Member 2) can reference them directly.
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.models.zone import Zone
from app.models.sensor import Sensor
from app.models.worker import Worker

# ── Stable demo IDs ───────────────────────────────────────────────────────────
PLANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

ZONE_IDS = {
    "zone-01-degassing":      uuid.UUID("10000000-0000-0000-0000-000000000001"),
    "zone-02-castfloor":      uuid.UUID("10000000-0000-0000-0000-000000000002"),
    "zone-03-pump-room":      uuid.UUID("10000000-0000-0000-0000-000000000003"),
    "zone-04-storage":        uuid.UUID("10000000-0000-0000-0000-000000000004"),
    "zone-05-confined-tank":  uuid.UUID("10000000-0000-0000-0000-000000000005"),
}

DEMO_ZONES = [
    {"id": ZONE_IDS["zone-01-degassing"],     "name": "Zone 01 — Degassing Unit",    "hazard_class": "gas",           "slug": "zone-01-degassing",     "current_risk_score": 0},
    {"id": ZONE_IDS["zone-02-castfloor"],     "name": "Zone 02 — Cast Floor",         "hazard_class": "thermal",       "slug": "zone-02-castfloor",     "current_risk_score": 0},
    {"id": ZONE_IDS["zone-03-pump-room"],     "name": "Zone 03 — Pump Room",          "hazard_class": "mechanical",    "slug": "zone-03-pump-room",     "current_risk_score": 0},
    {"id": ZONE_IDS["zone-04-storage"],       "name": "Zone 04 — Hazmat Storage",     "hazard_class": "general",       "slug": "zone-04-storage",       "current_risk_score": 0},
    {"id": ZONE_IDS["zone-05-confined-tank"], "name": "Zone 05 — Confined Tank Entry","hazard_class": "confined_space","slug": "zone-05-confined-tank", "current_risk_score": 0},
]

DEMO_SENSORS = [
    # Zone 01
    {"zone_id": ZONE_IDS["zone-01-degassing"], "name": "Gas Sensor A1", "sensor_type": "gas", "unit": "ppm", "statutory_threshold": 100.0, "warning_threshold": 60.0},
    {"zone_id": ZONE_IDS["zone-01-degassing"], "name": "Gas Sensor A2", "sensor_type": "gas", "unit": "ppm", "statutory_threshold": 100.0, "warning_threshold": 60.0},
    {"zone_id": ZONE_IDS["zone-01-degassing"], "name": "Temp Sensor A3", "sensor_type": "temperature", "unit": "celsius", "statutory_threshold": 80.0, "warning_threshold": 60.0},
    # Zone 02
    {"zone_id": ZONE_IDS["zone-02-castfloor"], "name": "Temp Sensor B1", "sensor_type": "temperature", "unit": "celsius", "statutory_threshold": 250.0, "warning_threshold": 200.0},
    {"zone_id": ZONE_IDS["zone-02-castfloor"], "name": "Vibration Sensor B2", "sensor_type": "vibration", "unit": "mm/s", "statutory_threshold": 10.0, "warning_threshold": 7.0},
    # Zone 03
    {"zone_id": ZONE_IDS["zone-03-pump-room"], "name": "Pressure Sensor C1", "sensor_type": "pressure", "unit": "bar", "statutory_threshold": 8.0, "warning_threshold": 6.5},
    {"zone_id": ZONE_IDS["zone-03-pump-room"], "name": "Vibration Sensor C2", "sensor_type": "vibration", "unit": "mm/s", "statutory_threshold": 10.0, "warning_threshold": 7.0},
    # Zone 04
    {"zone_id": ZONE_IDS["zone-04-storage"], "name": "Gas Sensor D1", "sensor_type": "gas", "unit": "ppm", "statutory_threshold": 50.0, "warning_threshold": 30.0},
    # Zone 05
    {"zone_id": ZONE_IDS["zone-05-confined-tank"], "name": "O2 Sensor E1", "sensor_type": "gas", "unit": "ppm", "statutory_threshold": 19.5, "warning_threshold": 19.8},
    {"zone_id": ZONE_IDS["zone-05-confined-tank"], "name": "Temp Sensor E2", "sensor_type": "temperature", "unit": "celsius", "statutory_threshold": 45.0, "warning_threshold": 35.0},
]

DEMO_WORKERS = [
    {"plant_id": PLANT_ID, "name": "Ravi Kumar",    "badge_id": "W001", "role": "Welder",          "phone": "+919000000001"},
    {"plant_id": PLANT_ID, "name": "Suman Das",     "badge_id": "W002", "role": "Process Tech",    "phone": "+919000000002"},
    {"plant_id": PLANT_ID, "name": "Amit Singh",    "badge_id": "W003", "role": "Safety Officer",  "phone": "+919000000003"},
    {"plant_id": PLANT_ID, "name": "Priya Nair",    "badge_id": "W004", "role": "Maintenance",     "phone": "+919000000004"},
]

DEMO_USERS = [
    {"email": "officer@sentinelgrid.demo",  "password": "Demo@1234", "role": "safety_officer", "full_name": "Amit Singh"},
    {"email": "admin@sentinelgrid.demo",    "password": "Demo@1234", "role": "plant_admin",    "full_name": "Dr. Kavitha Rao"},
    {"email": "auditor@sentinelgrid.demo",  "password": "Demo@1234", "role": "auditor",        "full_name": "Suresh Mehta"},
]


def deterministic_sensor_id(zone_id: uuid.UUID, sensor_type: str) -> uuid.UUID:
    """Match ingest_adapters.try_normalize_sensor_ingest UUID5 scheme."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"{zone_id}:{sensor_type}")


async def seed(session: AsyncSession) -> None:
    from sqlalchemy import select

    print("🌱 Seeding demo data...")

    # Zones
    for z in DEMO_ZONES:
        exists = await session.execute(select(Zone).where(Zone.id == z["id"]))
        if not exists.scalar_one_or_none():
            session.add(Zone(plant_id=PLANT_ID, **z))
            print(f"  ✅ Zone: {z['name']}")
    await session.flush()

    # Sensors (deterministic IDs so simulator ingest resolves correctly)
    for s in DEMO_SENSORS:
        sensor_id = deterministic_sensor_id(s["zone_id"], s["sensor_type"])
        exists = await session.execute(select(Sensor).where(Sensor.id == sensor_id))
        if not exists.scalar_one_or_none():
            session.add(Sensor(id=sensor_id, **s))
    print(f"  ✅ {len(DEMO_SENSORS)} sensors ensured")

    # Workers
    for w in DEMO_WORKERS:
        exists = await session.execute(select(Worker).where(Worker.badge_id == w["badge_id"]))
        if not exists.scalar_one_or_none():
            session.add(Worker(**w))
    print(f"  ✅ {len(DEMO_WORKERS)} workers ensured")

    # Users
    for u in DEMO_USERS:
        exists = await session.execute(select(User).where(User.email == u["email"]))
        if not exists.scalar_one_or_none():
            session.add(User(
                plant_id=PLANT_ID,
                email=u["email"],
                password_hash=get_password_hash(u["password"]),
                role=u["role"],
                full_name=u["full_name"],
                is_active=True,
            ))
            print(f"  ✅ User: {u['email']} ({u['role']})")

    await session.commit()
    print("\n✨ Seed complete!")
    print("\nDemo credentials:")
    for u in DEMO_USERS:
        print(f"  {u['email']} / {u['password']}  [{u['role']}]")


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
