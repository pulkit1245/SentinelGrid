"""
simulator_bridge.py — Backend bridge for the SentinelGrid Sensor Simulator.

Accepts batched sensor readings from the external simulator process (port 8002)
and broadcasts them to all connected dashboard WebSocket clients via the
existing broadcast_event infrastructure.

This is the ONLY file that bridges the simulator and the frontend — no other
existing files need to be modified to support the simulator.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.api.v1.dashboard_ws import broadcast_event
from app.core.config import settings
from app.middlewares.auth_middleware import verify_service_token
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulator", tags=["simulator-bridge"])

# ── Per-zone SMS debounce (zone_name → last SMS epoch) ───────────────────────
SMS_COOLDOWN_SECONDS = 300          # 5 min — one SMS per zone per incident
_last_sms: dict[str, float] = {}    # zone_name → time.monotonic() of last send
_prev_zone_status: dict[str, str] = {}  # zone_name → previous status string


# ── asyncpg DSN (convert SQLAlchemy URL → asyncpg format) ─────────────────────
def _pg_dsn() -> str:
    """Convert 'postgresql+asyncpg://...' to 'postgresql://...' for asyncpg."""
    return str(settings.DATABASE_URL).replace("postgresql+asyncpg://", "postgresql://")


# ── Payload models (mirror backend/app/simulator/models.py) ───────────────────

class SensorReadingPayload(BaseModel):
    sensor_id: str
    sensor_name: str
    sensor_type: str
    zone_id: str
    zone_name: str
    x: float
    y: float
    current_value: float
    unit: str
    status: str
    threshold_warning: float
    threshold_high: float
    threshold_critical: float
    battery_level: int
    signal_strength: int
    last_updated: str
    incident_active: bool = False
    incident_type: str | None = None


class ZoneHealthPayload(BaseModel):
    zone_id: str
    zone_name: str
    risk_score: int
    status: str
    active_incidents: list[str]
    affected_sensors: list[str]
    sensor_count: int
    last_updated: str


class BatchPayload(BaseModel):
    readings: list[SensorReadingPayload]
    zone_health: list[ZoneHealthPayload]
    tick: int
    timestamp: str


# ── Bridge endpoint ────────────────────────────────────────────────────────────

@router.post(
    "/batch",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Accept batched sensor readings from the simulator and broadcast via WebSocket",
)
async def ingest_batch(
    payload: BatchPayload,
    _: None = Depends(verify_service_token),
) -> dict[str, Any]:
    """
    Called every second by the simulator scheduler.
    Broadcasts each sensor reading and zone health update to all
    connected dashboard clients via the existing WebSocket manager.
    """
    reading_count = len(payload.readings)
    zone_count = len(payload.zone_health)

    # Broadcast individual sensor updates
    for reading in payload.readings:
        await broadcast_event(
            "sensor_update",
            {
                # Match SensorMarker interface in frontend types exactly
                "id": reading.sensor_id,
                "sensor_name": reading.sensor_name,
                "sensor_type": reading.sensor_type,
                "zone_id": reading.zone_id,
                "zone_name": reading.zone_name,
                "x": reading.x,
                "y": reading.y,
                "current_value": reading.current_value,
                "unit": reading.unit,
                "status": reading.status,
                "threshold_warning": reading.threshold_warning,
                "threshold_high": reading.threshold_high,
                "threshold_critical": reading.threshold_critical,
                "battery_level": reading.battery_level,
                "signal_strength": reading.signal_strength,
                "last_updated": reading.last_updated,
                "incident_active": reading.incident_active,
                "incident_type": reading.incident_type,
            },
        )

    # Broadcast zone health updates + fire SMS on first critical transition
    for zone_health in payload.zone_health:
        await broadcast_event(
            "zone_health_update",
            zone_health.model_dump(),
        )

        # ── SMS alert logic ──────────────────────────────────────────────
        zname   = zone_health.zone_name
        cur_st  = zone_health.status
        prev_st = _prev_zone_status.get(zname, "healthy")
        now_t   = time.monotonic()
        last_t  = _last_sms.get(zname, 0.0)

        # Send SMS only when zone TRANSITIONS INTO critical AND cooldown elapsed
        if (
            cur_st == "critical"
            and prev_st != "critical"
            and (now_t - last_t) >= SMS_COOLDOWN_SECONDS
        ):
            _last_sms[zname] = now_t
            # Fire SMS in background (non-blocking)
            import asyncio
            asyncio.create_task(
                notification_service.send_critical_sensor_sms(
                    zone_name=zname,
                    incident_type=" + ".join(zone_health.active_incidents) or "UNKNOWN",
                    affected_sensors=zone_health.affected_sensors,
                    risk_score=zone_health.risk_score,
                    active_incidents=zone_health.active_incidents,
                )
            )
            logger.warning(
                "SMS alert queued for zone=%s risk=%d",
                zname, zone_health.risk_score,
            )

        _prev_zone_status[zname] = cur_st

    # Broadcast a tick heartbeat every 10 ticks (for analytics / keepalive)
    if payload.tick % 10 == 0:
        await broadcast_event(
            "simulator_tick",
            {
                "tick": payload.tick,
                "timestamp": payload.timestamp,
                "sensor_count": reading_count,
                "zone_count": zone_count,
            },
        )

    # ── Persist risk scores to DB every 5 ticks ──────────────────────────────
    if payload.tick % 5 == 0:
        try:
            conn = await asyncpg.connect(_pg_dsn())
            try:
                for zh in payload.zone_health:
                    await conn.execute(
                        "UPDATE zones SET current_risk_score = $1 "
                        "WHERE LOWER(TRIM(name)) = LOWER(TRIM($2))",
                        min(100, max(0, zh.risk_score)),
                        zh.zone_name,
                    )
            finally:
                await conn.close()
        except Exception as exc:
            logger.warning("DB risk score update failed: %r", exc)

    if payload.tick % 60 == 0:
        logger.info(
            "Simulator bridge: tick=%d readings=%d zones=%d",
            payload.tick, reading_count, zone_count,
        )

    return {
        "status": "accepted",
        "tick": payload.tick,
        "readings_broadcast": reading_count,
        "zones_broadcast": zone_count,
    }


@router.get(
    "/status",
    summary="Bridge health check",
)
async def bridge_status() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "simulator-bridge",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
