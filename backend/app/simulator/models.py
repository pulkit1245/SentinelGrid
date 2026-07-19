from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class IncidentPhase(Enum):
    PENDING = 'PENDING'
    ESCALATING = 'ESCALATING'
    PEAK = 'PEAK'
    RECOVERING = 'RECOVERING'
    RESOLVED = 'RESOLVED'

class IncidentType(Enum):
    GAS_LEAK = 'GAS_LEAK'
    FIRE = 'FIRE'
    SMOKE = 'SMOKE'
    OVERHEATING = 'OVERHEATING'
    PRESSURE_DROP = 'PRESSURE_DROP'
    PRESSURE_SPIKE = 'PRESSURE_SPIKE'
    VIBRATION = 'VIBRATION'
    FLOOD = 'FLOOD'
    SENSOR_OFFLINE = 'SENSOR_OFFLINE'

class SensorStatus(Enum):
    HEALTHY = 'HEALTHY'
    WARNING = 'WARNING'
    HIGH_RISK = 'HIGH_RISK'
    CRITICAL = 'CRITICAL'
    OFFLINE = 'OFFLINE'

class SensorConfig(BaseModel):
    id: str
    zone_id: str
    zone_name: str
    name: str
    sensor_type: str
    x: float
    y: float
    base_value: float
    noise_std: float
    unit: str
    threshold_warning: float
    threshold_high: float
    threshold_critical: float
    battery_base: int
    signal_base: int

class SensorReading(BaseModel):
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

class SimulatedIncident(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_type: IncidentType
    zone_id: str
    zone_name: str
    affected_sensor_ids: list[str]
    phase: IncidentPhase = IncidentPhase.ESCALATING
    severity: str
    start_time: str
    end_time: str | None = None
    peak_value: float = 0.0
    peak_sensor_id: str | None = None
    escalation_seconds: float
    peak_hold_seconds: float
    recovery_seconds: float
    elapsed_seconds: float = 0.0
    resolution_status: str = 'active'

class ZoneHealth(BaseModel):
    zone_id: str
    zone_name: str
    risk_score: int
    status: str
    active_incidents: list[str]
    affected_sensors: list[str]
    sensor_count: int
    last_updated: str

class BatchPayload(BaseModel):
    readings: list[SensorReading]
    zone_health: list[ZoneHealth]
    tick: int
    timestamp: str

class SimulatorStatus(BaseModel):
    running: bool
    tick_count: int
    sensor_count: int
    zone_count: int
    active_incidents: int
    uptime_seconds: float
    last_tick: str | None
    bridge_url: str
