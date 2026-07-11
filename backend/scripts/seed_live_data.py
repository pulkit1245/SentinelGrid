#!/usr/bin/env python3
"""
Seed LIVE demo data — alerts, permits, sensor readings, and risk scores.
Run with:
    python -m scripts.seed_live_data
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.alert import Alert
from app.models.permit import Permit
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.models.zone import Zone
from app.models.worker import Worker
from app.models.user import User

# ── Stable IDs (from seed_demo_data.py) ──────────────────────────────────────
PLANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

ZONE_IDS = {
    "zone-01-degassing":      uuid.UUID("10000000-0000-0000-0000-000000000001"),
    "zone-02-castfloor":      uuid.UUID("10000000-0000-0000-0000-000000000002"),
    "zone-03-pump-room":      uuid.UUID("10000000-0000-0000-0000-000000000003"),
    "zone-04-storage":        uuid.UUID("10000000-0000-0000-0000-000000000004"),
    "zone-05-confined-tank":  uuid.UUID("10000000-0000-0000-0000-000000000005"),
}

def now() -> datetime:
    return datetime.now(timezone.utc)

def mins_ago(n: int) -> datetime:
    return now() - timedelta(minutes=n)

def hours_ago(n: float) -> datetime:
    return now() - timedelta(hours=n)


async def seed_risk_scores(session: AsyncSession) -> None:
    """Give each zone a realistic risk score."""
    risk_map = {
        ZONE_IDS["zone-01-degassing"]:     78,   # HIGH — gas detection
        ZONE_IDS["zone-02-castfloor"]:     62,   # MEDIUM — thermal
        ZONE_IDS["zone-03-pump-room"]:     41,   # MEDIUM-LOW — vibration
        ZONE_IDS["zone-04-storage"]:       23,   # LOW
        ZONE_IDS["zone-05-confined-tank"]: 89,   # CRITICAL — confined space
    }
    for zone_id, score in risk_map.items():
        await session.execute(
            update(Zone).where(Zone.id == zone_id).values(current_risk_score=score)
        )
    print("  ✅ Risk scores updated")


async def seed_alerts(session: AsyncSession, admin_user_id: uuid.UUID) -> None:
    """Create realistic active and historical alerts."""
    alerts = [
        # ─── ACTIVE CRITICAL ────────────────────────────────────────────────
        Alert(
            zone_id=ZONE_IDS["zone-05-confined-tank"],
            severity="critical",
            title="O₂ Deficiency + Permit Overlap — Confined Tank E",
            description=(
                "Oxygen level dropped to 17.2 % (statutory min 19.5 %). "
                "Two hot-work permits are simultaneously active in the same confined space. "
                "Immediate evacuation required. SCBA mandatory for rescue team entry."
            ),
            graph_path=[
                {"node": "O2-Sensor-E1", "value": 17.2, "threshold": 19.5, "type": "sensor"},
                {"node": "Permit-HW-042", "overlap": True, "type": "permit"},
                {"node": "Permit-CS-011", "overlap": True, "type": "permit"},
                {"node": "Zone-05", "risk": 89, "type": "zone"},
            ],
            triggered_at=mins_ago(12),
            is_active=True,
        ),
        Alert(
            zone_id=ZONE_IDS["zone-01-degassing"],
            severity="critical",
            title="H₂S Spike Above Statutory Limit — Degassing Unit",
            description=(
                "Gas Sensor A1 recorded 112 ppm H₂S (statutory limit 100 ppm). "
                "Sensor A2 corroborates at 98 ppm. Hot-work permit HW-039 remains active. "
                "Compound risk: ignition source present in high-gas zone."
            ),
            graph_path=[
                {"node": "Gas-Sensor-A1", "value": 112.0, "threshold": 100.0, "type": "sensor"},
                {"node": "Gas-Sensor-A2", "value": 98.0, "threshold": 100.0, "type": "sensor"},
                {"node": "Permit-HW-039", "status": "active", "type": "permit"},
            ],
            triggered_at=mins_ago(34),
            is_active=True,
        ),
        # ─── ACTIVE WARNING ─────────────────────────────────────────────────
        Alert(
            zone_id=ZONE_IDS["zone-02-castfloor"],
            severity="warning",
            title="Elevated Temperature — Cast Floor B",
            description=(
                "Temp Sensor B1 at 218 °C, approaching the 250 °C statutory threshold. "
                "Vibration Sensor B2 simultaneously showing micro-seismic activity at 6.8 mm/s. "
                "Possible mould shell instability. Recommend temporary halt of pour."
            ),
            graph_path=[
                {"node": "Temp-Sensor-B1", "value": 218.0, "threshold": 250.0, "type": "sensor"},
                {"node": "Vibration-B2", "value": 6.8, "threshold": 7.0, "type": "sensor"},
            ],
            triggered_at=mins_ago(7),
            is_active=True,
        ),
        Alert(
            zone_id=ZONE_IDS["zone-03-pump-room"],
            severity="warning",
            title="Pressure Anomaly — Pump Room C",
            description=(
                "Pressure Sensor C1 registered 7.1 bar, exceeding warning threshold of 6.5 bar. "
                "Vibration Sensor C2 at 8.1 mm/s (above 7.0 mm/s warning). "
                "Risk of pump cavitation or seal failure."
            ),
            graph_path=[
                {"node": "Pressure-C1", "value": 7.1, "threshold": 6.5, "type": "sensor"},
                {"node": "Vibration-C2", "value": 8.1, "threshold": 7.0, "type": "sensor"},
            ],
            triggered_at=mins_ago(51),
            is_active=True,
        ),
        # ─── ACTIVE WATCH ───────────────────────────────────────────────────
        Alert(
            zone_id=ZONE_IDS["zone-04-storage"],
            severity="watch",
            title="Gas Reading Rising — Hazmat Storage D",
            description=(
                "Gas Sensor D1 trending upward: 28 ppm over past 20 minutes (warning threshold 30 ppm). "
                "No permits currently active. Monitor closely."
            ),
            graph_path=[
                {"node": "Gas-Sensor-D1", "value": 28.0, "threshold": 30.0, "type": "sensor"},
            ],
            triggered_at=mins_ago(21),
            is_active=True,
        ),
        # ─── CONFIRMED (historical) ──────────────────────────────────────────
        Alert(
            zone_id=ZONE_IDS["zone-01-degassing"],
            severity="warning",
            title="Gas Sensor A2 Drift — Calibration Required",
            description="Sensor A2 showed intermittent 15 % high bias. Calibration performed and confirmed.",
            graph_path=[{"node": "Gas-Sensor-A2", "drift_pct": 15, "type": "sensor"}],
            triggered_at=hours_ago(6),
            confirmed_by=admin_user_id,
            confirmed_at=hours_ago(5),
            is_active=False,
        ),
        Alert(
            zone_id=ZONE_IDS["zone-03-pump-room"],
            severity="info",
            title="Scheduled Maintenance — Pump C started",
            description="Planned maintenance window. Permit CS-009 issued. All clear after 2 hrs.",
            graph_path=[],
            triggered_at=hours_ago(10),
            confirmed_by=admin_user_id,
            confirmed_at=hours_ago(8),
            is_active=False,
        ),
    ]

    for a in alerts:
        session.add(a)

    print(f"  ✅ {len(alerts)} alerts created ({sum(1 for a in alerts if a.is_active)} active)")


async def seed_permits(
    session: AsyncSession,
    workers: list[Worker],
    admin_user_id: uuid.UUID,
) -> None:
    """Create active and historical permits for each zone."""
    w = {w.badge_id: w.id for w in workers}

    def _pid(badge: str) -> uuid.UUID | None:
        return w.get(badge)

    permits = [
        # ─── ACTIVE ─────────────────────────────────────────────────────────
        Permit(
            zone_id=ZONE_IDS["zone-01-degassing"],
            permit_type="hot_work",
            issued_to_worker_id=_pid("W001"),  # Ravi Kumar — Welder
            issued_by_user_id=admin_user_id,
            valid_from=hours_ago(1),
            valid_to=now() + timedelta(hours=3),
            status="active",
            notes="Welding repair on degassing column B. Gas monitoring mandatory.",
        ),
        Permit(
            zone_id=ZONE_IDS["zone-05-confined-tank"],
            permit_type="confined_space",
            issued_to_worker_id=_pid("W002"),  # Suman Das
            issued_by_user_id=admin_user_id,
            valid_from=hours_ago(0.5),
            valid_to=now() + timedelta(hours=2),
            status="active",
            notes="Tank E internal inspection. SCBA required. Buddy system mandatory.",
        ),
        Permit(
            zone_id=ZONE_IDS["zone-05-confined-tank"],
            permit_type="hot_work",
            issued_to_worker_id=_pid("W001"),
            issued_by_user_id=admin_user_id,
            valid_from=hours_ago(0.25),
            valid_to=now() + timedelta(hours=1.5),
            status="active",
            notes="⚠️ OVERLAP — hot-work permit issued while confined_space permit active in same zone!",
        ),
        Permit(
            zone_id=ZONE_IDS["zone-02-castfloor"],
            permit_type="hot_work",
            issued_to_worker_id=_pid("W001"),
            issued_by_user_id=admin_user_id,
            valid_from=hours_ago(2),
            valid_to=now() + timedelta(hours=2),
            status="active",
            notes="Electrode replacement at tundish. PPE Level 3.",
        ),
        Permit(
            zone_id=ZONE_IDS["zone-03-pump-room"],
            permit_type="electrical",
            issued_to_worker_id=_pid("W004"),  # Priya Nair — Maintenance
            issued_by_user_id=admin_user_id,
            valid_from=hours_ago(3),
            valid_to=now() + timedelta(hours=1),
            status="active",
            notes="Pump C motor inspection. LOTO enforced.",
        ),
        # ─── CLOSED / HISTORICAL ────────────────────────────────────────────
        Permit(
            zone_id=ZONE_IDS["zone-04-storage"],
            permit_type="excavation",
            issued_to_worker_id=_pid("W003"),
            issued_by_user_id=admin_user_id,
            valid_from=hours_ago(12),
            valid_to=hours_ago(8),
            status="closed",
            notes="Drainage channel excavation completed.",
        ),
        Permit(
            zone_id=ZONE_IDS["zone-01-degassing"],
            permit_type="hot_work",
            issued_to_worker_id=_pid("W001"),
            issued_by_user_id=admin_user_id,
            valid_from=hours_ago(24),
            valid_to=hours_ago(20),
            status="revoked",
            notes="Revoked: gas reading spiked during work. Area evacuated.",
        ),
    ]

    for p in permits:
        session.add(p)

    active_count = sum(1 for p in permits if p.status == "active")
    print(f"  ✅ {len(permits)} permits created ({active_count} active)")


async def seed_sensor_readings(session: AsyncSession, sensors: list[Sensor]) -> None:
    """
    Create 48 hours of sensor readings at 5-minute intervals for every sensor.
    Values are realistic and trending toward warning/critical levels in the last 2 hours.
    """
    sensor_profiles = {
        # gas sensors — ppm, threshold 100
        "gas": {
            "base": 35.0, "noise": 8.0, "spike_factor": 2.5,
            "recent_trend": 1.8,   # readings climb toward threshold
        },
        # temperature — °C
        "temperature": {
            "base": 140.0, "noise": 12.0, "spike_factor": 1.6,
            "recent_trend": 2.2,
        },
        # pressure — bar, threshold 8.0
        "pressure": {
            "base": 5.2, "noise": 0.4, "spike_factor": 1.5,
            "recent_trend": 0.08,
        },
        # vibration — mm/s, threshold 10
        "vibration": {
            "base": 3.5, "noise": 0.8, "spike_factor": 2.2,
            "recent_trend": 0.15,
        },
    }

    readings: list[SensorReading] = []
    interval_minutes = 5
    hours_back = 48
    total_points = (hours_back * 60) // interval_minutes

    rng = random.Random(42)  # reproducible

    for sensor in sensors:
        profile = sensor_profiles.get(sensor.sensor_type, sensor_profiles["gas"])
        base = profile["base"]
        noise = profile["noise"]
        spike = profile["spike_factor"]
        trend = profile["recent_trend"]

        # threshold — use statutory if available, else a reasonable default
        threshold = sensor.statutory_threshold or base * 2.5

        for i in range(total_points):
            ts = now() - timedelta(minutes=(total_points - i) * interval_minutes)
            age_hours = (total_points - i) * interval_minutes / 60

            # Base sinusoidal pattern (day/night cycle)
            sinusoidal = base + noise * 0.4 * (
                1 + 0.5 * (1 - age_hours / hours_back)  # slowly rising
            )

            # Add random noise
            val = sinusoidal + rng.gauss(0, noise * 0.3)

            # Last 2 hours: trend upward (toward or past threshold in critical zones)
            if age_hours <= 2:
                hours_into_trend = 2 - age_hours
                val += trend * hours_into_trend * 60 / interval_minutes * 0.4

            # Occasional micro-spikes
            if rng.random() < 0.04:
                val *= rng.uniform(1.1, spike * 0.6)

            val = max(0.0, val)

            readings.append(SensorReading(
                id=uuid.uuid4(),
                sensor_id=sensor.id,
                zone_id=sensor.zone_id,
                reading_value=round(val, 2),
                recorded_at=ts,
            ))

    # Bulk insert in chunks of 500
    chunk_size = 500
    for start in range(0, len(readings), chunk_size):
        chunk = readings[start:start + chunk_size]
        session.add_all(chunk)
        await session.flush()

    print(f"  ✅ {len(readings):,} sensor readings created "
          f"({total_points} pts × {len(sensors)} sensors, 48 h @ 5-min interval)")


async def seed(session: AsyncSession) -> None:
    print("\n🌱 Seeding live demo data...")

    # ── Fetch references ──────────────────────────────────────────────────────
    result = await session.execute(select(Sensor))
    sensors: list[Sensor] = list(result.scalars().all())

    result = await session.execute(select(Worker))
    workers: list[Worker] = list(result.scalars().all())

    result = await session.execute(
        select(User).where(User.role == "plant_admin")
    )
    admin_user = result.scalar_one_or_none()
    admin_user_id: uuid.UUID = admin_user.id if admin_user else uuid.uuid4()

    if not sensors:
        print("  ⚠️  No sensors found — run seed_demo_data.py first!")
        return

    # ── Seed each entity ─────────────────────────────────────────────────────
    await seed_risk_scores(session)
    await seed_alerts(session, admin_user_id)
    await seed_permits(session, workers, admin_user_id)
    await seed_sensor_readings(session, sensors)

    await session.commit()

    print("\n✨ Live data seed complete!")
    print("   Dashboard should now show:")
    print("   • 5 active alerts (2 critical, 2 warning, 1 watch)")
    print("   • 5 active permits (including 1 dangerous overlap)")
    print("   • Risk scores: Zone 05 → 89, Zone 01 → 78, Zone 02 → 62, …")
    print("   • 48 h of sensor readings for all sparklines")


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
