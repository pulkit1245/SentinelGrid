"""
incidents.py — Incident lifecycle manager for SentinelGrid Simulator.

Manages the creation, escalation, and resolution of simulated industrial
incidents. Each incident targets specific sensor types in a zone and
drives their values through a sigmoid escalation curve, then recovers.
"""
from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from backend.app.simulator.models import (
    IncidentPhase,
    IncidentType,
    SimulatedIncident,
)

if TYPE_CHECKING:
    from backend.app.simulator.engine import SensorEngine, IncidentEffect

logger = logging.getLogger(__name__)


# ── Incident type → sensor type mapping ───────────────────────────────────────

INCIDENT_SENSOR_MAP: dict[IncidentType, list[str]] = {
    IncidentType.GAS_LEAK:        ["gas"],
    IncidentType.FIRE:            ["temperature", "smoke"],
    IncidentType.SMOKE:           ["smoke"],
    IncidentType.OVERHEATING:     ["temperature"],
    IncidentType.PRESSURE_DROP:   ["pressure"],
    IncidentType.PRESSURE_SPIKE:  ["pressure"],
    IncidentType.VIBRATION:       ["vibration"],
    IncidentType.FLOOD:           ["water_level", "humidity"],
    IncidentType.SENSOR_OFFLINE:  ["*"],
}

# ── Incident parameters ────────────────────────────────────────────────────────

INCIDENT_PARAMS: dict[IncidentType, dict] = {
    IncidentType.GAS_LEAK: {
        "peak_multiplier": 40.0,
        "escalation_seconds": 45,
        "peak_hold_seconds": 60,
        "recovery_seconds": 120,
        "auto_prob": 0.45,
        "auto_interval": (50, 70),   # ~1 min
    },
    IncidentType.FIRE: {
        "peak_multiplier_temp": 4.5,
        "peak_multiplier_smoke": 80.0,
        "escalation_seconds": 40,
        "peak_hold_seconds": 60,
        "recovery_seconds": 180,
        "auto_prob": 0.35,
        "auto_interval": (50, 70),   # ~1 min
    },
    IncidentType.SMOKE: {
        "peak_multiplier": 60.0,
        "escalation_seconds": 35,
        "peak_hold_seconds": 45,
        "recovery_seconds": 120,
        "auto_prob": 0.40,
        "auto_interval": (50, 70),   # ~1 min
    },
    IncidentType.OVERHEATING: {
        "peak_multiplier": 3.2,
        "escalation_seconds": 50,
        "peak_hold_seconds": 60,
        "recovery_seconds": 120,
        "auto_prob": 0.50,
        "auto_interval": (50, 70),   # ~1 min
    },
    IncidentType.PRESSURE_SPIKE: {
        "peak_multiplier": 0.35,
        "escalation_seconds": 30,
        "peak_hold_seconds": 40,
        "recovery_seconds": 90,
        "auto_prob": 0.40,
        "auto_interval": (50, 70),   # ~1 min
    },
    IncidentType.PRESSURE_DROP: {
        "peak_multiplier": -0.55,
        "escalation_seconds": 35,
        "peak_hold_seconds": 40,
        "recovery_seconds": 90,
        "auto_prob": 0.35,
        "auto_interval": (50, 70),   # ~1 min
    },
    IncidentType.VIBRATION: {
        "peak_multiplier": 7.0,
        "escalation_seconds": 30,
        "peak_hold_seconds": 60,
        "recovery_seconds": 90,
        "auto_prob": 0.55,
        "auto_interval": (50, 70),   # ~1 min
    },
    IncidentType.FLOOD: {
        "peak_multiplier_water": 18.0,
        "peak_multiplier_humidity": 0.7,
        "escalation_seconds": 60,
        "peak_hold_seconds": 120,
        "recovery_seconds": 300,
        "auto_prob": 0.25,
        "auto_interval": (50, 70),   # ~1 min
    },
    IncidentType.SENSOR_OFFLINE: {
        "offline_seconds": 30,
        "auto_prob": 0.30,
        "auto_interval": (50, 70),   # ~1 min
    },
}


class IncidentManager:
    """
    Manages the full lifecycle of simulated incidents.

    - Tracks active and historical incidents
    - Drives SensorEngine IncidentEffect objects
    - Triggers automatic incidents on probabilistic schedule
    """

    def __init__(self) -> None:
        self._active: dict[str, SimulatedIncident] = {}   # incident_id → SimulatedIncident
        self._history: list[SimulatedIncident] = []
        self._auto_timers: dict[IncidentType, float] = {}  # seconds until next auto trigger
        self._engines: dict[str, SensorEngine] = {}        # sensor_id → engine (set by scheduler)
        self._zone_sensor_map: dict[str, list[str]] = {}   # zone_id → list of sensor_ids

    def register_engines(
        self,
        engines: dict[str, "SensorEngine"],
        zone_sensor_map: dict[str, list[str]],
    ) -> None:
        self._engines = engines
        self._zone_sensor_map = zone_sensor_map
        # Initialize auto timers with random initial delay
        for inc_type in IncidentType:
            if inc_type == IncidentType.SENSOR_OFFLINE:
                interval_range = INCIDENT_PARAMS[inc_type]["auto_interval"]
            else:
                interval_range = INCIDENT_PARAMS[inc_type]["auto_interval"]
            self._auto_timers[inc_type] = random.uniform(*interval_range)

    # ── Public trigger methods ─────────────────────────────────────────────────

    def trigger(
        self,
        incident_type: IncidentType,
        zone_id: str,
        sensor_id: str | None = None,
        duration: float | None = None,
        severity: str = "high",
    ) -> SimulatedIncident:
        """Manually trigger an incident. Called by REST endpoints."""
        return self._start_incident(incident_type, zone_id, sensor_id, duration, severity)

    def reset_all(self) -> None:
        """Reset all active incidents and return all sensors to baseline."""
        for engine in self._engines.values():
            engine.reset()
        for inc in self._active.values():
            inc.phase = IncidentPhase.RESOLVED
            inc.end_time = _now_iso()
            inc.resolution_status = "manually_reset"
            self._history.append(inc)
        self._active.clear()

    def reset_zone(self, zone_id: str) -> None:
        """Reset all incidents in a specific zone."""
        to_remove = []
        for inc_id, inc in self._active.items():
            if inc.zone_id == zone_id:
                for sid in inc.affected_sensor_ids:
                    if sid in self._engines:
                        self._engines[sid].reset()
                inc.phase = IncidentPhase.RESOLVED
                inc.end_time = _now_iso()
                inc.resolution_status = "manually_reset"
                self._history.append(inc)
                to_remove.append(inc_id)
        for inc_id in to_remove:
            del self._active[inc_id]

    # ── Tick (called every second by scheduler) ────────────────────────────────

    def tick(self, dt: float = 1.0) -> None:
        """Advance all timers; auto-trigger incidents; clean up resolved ones."""

        # Advance auto-trigger timers
        for inc_type, remaining in list(self._auto_timers.items()):
            self._auto_timers[inc_type] = remaining - dt
            if remaining <= 0:
                params = INCIDENT_PARAMS[inc_type]
                if random.random() < params["auto_prob"]:
                    self._auto_trigger(inc_type)
                # Reset timer
                interval_range = params["auto_interval"]
                self._auto_timers[inc_type] = random.uniform(*interval_range)

        # Update active incidents
        resolved_ids = []
        for inc_id, inc in self._active.items():
            inc.elapsed_seconds += dt

            if inc.phase == IncidentPhase.ESCALATING:
                if inc.elapsed_seconds >= inc.escalation_seconds:
                    inc.phase = IncidentPhase.PEAK
                    inc.elapsed_seconds = 0.0
            elif inc.phase == IncidentPhase.PEAK:
                if inc.elapsed_seconds >= inc.peak_hold_seconds:
                    inc.phase = IncidentPhase.RECOVERING
                    inc.elapsed_seconds = 0.0
            elif inc.phase == IncidentPhase.RECOVERING:
                if inc.elapsed_seconds >= inc.recovery_seconds:
                    inc.phase = IncidentPhase.RESOLVED
                    inc.end_time = _now_iso()
                    inc.resolution_status = "auto_resolved"
                    resolved_ids.append(inc_id)

        for inc_id in resolved_ids:
            inc = self._active.pop(inc_id)
            self._history.append(inc)
            logger.info("Incident %s resolved: %s", inc.incident_type.value, inc_id)

    # ── Queries ────────────────────────────────────────────────────────────────

    def active_for_zone(self, zone_id: str) -> list[SimulatedIncident]:
        return [i for i in self._active.values() if i.zone_id == zone_id]

    def active_ids_for_zone(self, zone_id: str) -> list[str]:
        return [i.incident_id for i in self.active_for_zone(zone_id)]

    def all_active(self) -> list[SimulatedIncident]:
        return list(self._active.values())

    def history(self) -> list[SimulatedIncident]:
        return self._history.copy()

    def all_incidents(self) -> list[SimulatedIncident]:
        return list(self._active.values()) + self._history

    # ── Internal ───────────────────────────────────────────────────────────────

    def _auto_trigger(self, inc_type: IncidentType) -> None:
        """Pick a random zone and trigger the incident automatically."""
        zones = list(self._zone_sensor_map.keys())
        if not zones:
            return
        zone_id = random.choice(zones)
        severity = random.choice(["medium", "high", "critical"])
        try:
            self._start_incident(inc_type, zone_id, None, None, severity)
            logger.info("Auto-triggered %s in %s", inc_type.value, zone_id)
        except Exception as exc:
            logger.warning("Auto-trigger failed for %s: %s", inc_type.value, exc)

    def _start_incident(
        self,
        incident_type: IncidentType,
        zone_id: str,
        sensor_id: str | None,
        duration: float | None,
        severity: str,
    ) -> SimulatedIncident:
        from backend.app.simulator.engine import IncidentEffect

        params = INCIDENT_PARAMS[incident_type]

        # Find target sensors
        target_type_filter = INCIDENT_SENSOR_MAP.get(incident_type, [])
        zone_sensor_ids = self._zone_sensor_map.get(zone_id, [])

        if sensor_id and sensor_id in self._engines:
            target_ids = [sensor_id]
        elif target_type_filter == ["*"]:
            # Sensor offline: pick one random sensor in zone
            target_ids = [random.choice(zone_sensor_ids)] if zone_sensor_ids else []
        else:
            target_ids = [
                sid for sid in zone_sensor_ids
                if sid in self._engines and self._engines[sid].config.sensor_type in target_type_filter
            ]

        if not target_ids:
            raise ValueError(f"No matching sensors in zone {zone_id} for {incident_type.value}")

        # Apply severity multiplier
        severity_factor = {"low": 0.4, "medium": 0.7, "high": 1.0, "critical": 1.3}.get(severity, 1.0)
        esc_s = params.get("escalation_seconds", 180) * (1 / severity_factor)
        peak_s = params.get("peak_hold_seconds", 60)
        rec_s = params.get("recovery_seconds", 360)

        if duration:
            total = esc_s + peak_s + rec_s
            scale = duration / total
            esc_s *= scale
            peak_s *= scale
            rec_s *= scale

        # Handle sensor-offline separately
        if incident_type == IncidentType.SENSOR_OFFLINE:
            offline_s = params.get("offline_seconds", 60)
            for tid in target_ids:
                if tid in self._engines:
                    self._engines[tid].set_offline(offline_s)

            inc = SimulatedIncident(
                incident_id=str(uuid.uuid4()),
                incident_type=incident_type,
                zone_id=zone_id,
                zone_name=self._get_zone_name(zone_id),
                affected_sensor_ids=target_ids,
                phase=IncidentPhase.PEAK,
                severity=severity,
                start_time=_now_iso(),
                escalation_seconds=0,
                peak_hold_seconds=offline_s,
                recovery_seconds=30,
            )
            self._active[inc.incident_id] = inc
            return inc

        # Apply effects to engines
        for tid in target_ids:
            engine = self._engines.get(tid)
            if not engine:
                continue
            base = engine.config.base_value

            # Determine peak delta for this sensor type
            stype = engine.config.sensor_type
            if incident_type == IncidentType.FIRE:
                if stype == "temperature":
                    pm = params.get("peak_multiplier_temp", 4.0)
                    peak_delta = base * (pm - 1.0) * severity_factor
                else:  # smoke
                    pm = params.get("peak_multiplier_smoke", 60.0)
                    peak_delta = base * pm * severity_factor
            elif incident_type == IncidentType.FLOOD:
                if stype == "water_level":
                    pm = params.get("peak_multiplier_water", 18.0)
                    peak_delta = base * pm * severity_factor
                else:  # humidity
                    pm = params.get("peak_multiplier_humidity", 0.7)
                    peak_delta = base * pm * severity_factor
            elif incident_type == IncidentType.PRESSURE_DROP:
                pm = params.get("peak_multiplier", -0.55)
                peak_delta = base * pm * severity_factor  # negative delta
            else:
                pm = params.get("peak_multiplier", 3.0)
                peak_delta = base * pm * severity_factor

            effect = IncidentEffect(
                incident_id=str(uuid.uuid4()),
                incident_type=incident_type.value,
                peak_delta=peak_delta,
                escalation_seconds=esc_s,
                peak_hold_seconds=peak_s,
                recovery_seconds=rec_s,
            )
            engine.add_incident(effect)

        inc = SimulatedIncident(
            incident_id=str(uuid.uuid4()),
            incident_type=incident_type,
            zone_id=zone_id,
            zone_name=self._get_zone_name(zone_id),
            affected_sensor_ids=target_ids,
            severity=severity,
            start_time=_now_iso(),
            escalation_seconds=esc_s,
            peak_hold_seconds=peak_s,
            recovery_seconds=rec_s,
        )
        self._active[inc.incident_id] = inc
        logger.info(
            "Started incident %s [%s] in zone %s affecting %s",
            incident_type.value, inc.incident_id[:8], zone_id, target_ids,
        )
        return inc

    def _get_zone_name(self, zone_id: str) -> str:
        from backend.app.simulator.config import load_zones
        zones = load_zones()
        for z in zones:
            if z["zone_id"] == zone_id:
                return z["zone_name"]
        return zone_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
