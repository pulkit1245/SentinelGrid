"""
routes.py — REST API for manual simulator control.

Provides endpoints to trigger industrial incidents, query sensor state,
reset simulation, and view incident history. All endpoints are CORS-open
since the simulator runs on a separate port (8002).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from backend.app.simulator.models import IncidentType, SimulatedIncident

if TYPE_CHECKING:
    from backend.app.simulator.scheduler import SimulatorScheduler

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request body models ────────────────────────────────────────────────────────

class IncidentRequest(BaseModel):
    zoneId: str
    sensorId: str | None = None
    duration: float | None = None          # seconds; None = use default
    severity: str = "high"                 # low / medium / high / critical


class OfflineRequest(BaseModel):
    sensorId: str
    duration: float = 60.0                 # seconds offline


# ── Helper to get scheduler from app state ─────────────────────────────────────

def _sched(request: Request) -> "SimulatorScheduler":
    return request.app.state.scheduler


# ── Status & sensor queries ────────────────────────────────────────────────────

@router.get("/status", summary="Simulator status and health")
async def get_status(request: Request) -> dict[str, Any]:
    return _sched(request).get_status().model_dump()


@router.get("/sensors", summary="All current sensor readings")
async def get_sensors(request: Request) -> list[dict[str, Any]]:
    return [r.model_dump() for r in _sched(request).get_latest_readings()]


@router.get("/sensors/{sensor_id}", summary="Single sensor current reading")
async def get_sensor(sensor_id: str, request: Request) -> dict[str, Any]:
    reading = _sched(request).get_reading(sensor_id)
    if not reading:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id!r} not found")
    return reading.model_dump()


@router.get("/zones/health", summary="Zone health aggregates")
async def get_zone_health(request: Request) -> list[dict[str, Any]]:
    sched = _sched(request)
    from backend.app.simulator.config import load_zones
    from backend.app.simulator.utils import compute_zone_health
    zones = load_zones()
    result = []
    for zone in zones:
        zid = zone["zone_id"]
        readings = [r for r in sched.get_latest_readings() if r.zone_id == zid]
        active_ids = sched.incidents.active_ids_for_zone(zid)
        health = compute_zone_health(readings, zid, zone["zone_name"], active_ids)
        result.append(health.model_dump())
    return result


# ── Incident log ───────────────────────────────────────────────────────────────

@router.get("/incidents", summary="Full incident history (active + resolved)")
async def get_incidents(request: Request) -> list[dict[str, Any]]:
    all_inc = _sched(request).incidents.all_incidents()
    return [i.model_dump() for i in all_inc]


@router.get("/incidents/active", summary="Active incidents only")
async def get_active_incidents(request: Request) -> list[dict[str, Any]]:
    return [i.model_dump() for i in _sched(request).incidents.all_active()]


# ── Manual incident triggers ───────────────────────────────────────────────────

def _trigger(request: Request, inc_type: IncidentType, body: IncidentRequest) -> dict[str, Any]:
    try:
        inc: SimulatedIncident = _sched(request).incidents.trigger(
            incident_type=inc_type,
            zone_id=body.zoneId,
            sensor_id=body.sensorId,
            duration=body.duration,
            severity=body.severity,
        )
        return {
            "status": "triggered",
            "incident_id": inc.incident_id,
            "incident_type": inc.incident_type.value,
            "zone_id": inc.zone_id,
            "severity": inc.severity,
            "affected_sensors": inc.affected_sensor_ids,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Trigger error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/simulate/fire", summary="Trigger a fire incident")
async def trigger_fire(body: IncidentRequest, request: Request) -> dict[str, Any]:
    return _trigger(request, IncidentType.FIRE, body)


@router.post("/simulate/gas-leak", summary="Trigger a gas leak incident")
async def trigger_gas_leak(body: IncidentRequest, request: Request) -> dict[str, Any]:
    return _trigger(request, IncidentType.GAS_LEAK, body)


@router.post("/simulate/smoke", summary="Trigger a smoke detection event")
async def trigger_smoke(body: IncidentRequest, request: Request) -> dict[str, Any]:
    return _trigger(request, IncidentType.SMOKE, body)


@router.post("/simulate/overheating", summary="Trigger machine overheating")
async def trigger_overheating(body: IncidentRequest, request: Request) -> dict[str, Any]:
    return _trigger(request, IncidentType.OVERHEATING, body)


@router.post("/simulate/pressure-drop", summary="Trigger pressure drop")
async def trigger_pressure_drop(body: IncidentRequest, request: Request) -> dict[str, Any]:
    return _trigger(request, IncidentType.PRESSURE_DROP, body)


@router.post("/simulate/pressure-spike", summary="Trigger pressure spike")
async def trigger_pressure_spike(body: IncidentRequest, request: Request) -> dict[str, Any]:
    return _trigger(request, IncidentType.PRESSURE_SPIKE, body)


@router.post("/simulate/vibration", summary="Trigger excessive vibration")
async def trigger_vibration(body: IncidentRequest, request: Request) -> dict[str, Any]:
    return _trigger(request, IncidentType.VIBRATION, body)


@router.post("/simulate/flood", summary="Trigger flood / water ingress")
async def trigger_flood(body: IncidentRequest, request: Request) -> dict[str, Any]:
    return _trigger(request, IncidentType.FLOOD, body)


@router.post("/simulate/sensor-offline", summary="Take a sensor offline")
async def trigger_offline(body: OfflineRequest, request: Request) -> dict[str, Any]:
    # Find zone for the sensor
    sched = _sched(request)
    engine = sched.engines.get(body.sensorId)
    if not engine:
        raise HTTPException(status_code=404, detail=f"Sensor {body.sensorId!r} not found")
    zone_id = engine.config.zone_id
    try:
        inc = sched.incidents.trigger(
            incident_type=IncidentType.SENSOR_OFFLINE,
            zone_id=zone_id,
            sensor_id=body.sensorId,
            duration=body.duration,
            severity="medium",
        )
        return {
            "status": "triggered",
            "incident_id": inc.incident_id,
            "sensor_id": body.sensorId,
            "offline_seconds": body.duration,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/simulate/reset", summary="Reset all incidents to baseline")
async def reset_all(request: Request) -> dict[str, Any]:
    _sched(request).incidents.reset_all()
    return {"status": "reset", "message": "All sensors returned to baseline"}


@router.post("/simulate/reset/{zone_id}", summary="Reset a specific zone to baseline")
async def reset_zone(zone_id: str, request: Request) -> dict[str, Any]:
    _sched(request).incidents.reset_zone(zone_id)
    return {"status": "reset", "zone_id": zone_id}
