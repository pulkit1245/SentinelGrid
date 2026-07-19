from __future__ import annotations
import math
import random
from datetime import datetime, timezone
from backend.app.simulator.models import SensorReading, ZoneHealth, SensorStatus

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def compute_status(value: float, threshold_warning: float, threshold_high: float, threshold_critical: float) -> str:
    """Return status string based on value vs thresholds. Handles both positive escalation (gas) and negative (pressure drop)."""
    abs_val = abs(value)
    abs_warn = abs(threshold_warning)
    abs_high = abs(threshold_high)
    abs_crit = abs(threshold_critical)
    
    if threshold_critical > threshold_warning:  # positive escalation
        if value >= threshold_critical:
            return 'critical'
        elif value >= threshold_high:
            return 'high_risk'
        elif value >= threshold_warning:
            return 'warning'
        return 'healthy'
    else:  # negative (pressure drop)
        if value <= threshold_critical:
            return 'critical'
        elif value <= threshold_high:
            return 'high_risk'
        elif value <= threshold_warning:
            return 'warning'
        return 'healthy'

def compute_zone_health(readings: list[SensorReading], zone_id: str, zone_name: str, active_incident_ids: list[str]) -> ZoneHealth:
    """Aggregate sensor readings into a zone health score 0-100."""
    if not readings:
        return ZoneHealth(
            zone_id=zone_id, zone_name=zone_name,
            risk_score=0, status='healthy',
            active_incidents=active_incident_ids,
            affected_sensors=[], sensor_count=0,
            last_updated=now_iso()
        )
    
    STATUS_WEIGHTS = {'healthy': 0, 'warning': 30, 'high_risk': 65, 'critical': 100, 'offline': 50}
    weights = [STATUS_WEIGHTS.get(r.status, 0) for r in readings]
    avg_risk = sum(weights) / len(weights)
    max_risk = max(weights)
    # 40% average + 60% max sensor  
    risk_score = int(avg_risk * 0.4 + max_risk * 0.6)
    risk_score = max(0, min(100, risk_score))
    
    if risk_score >= 75:
        status = 'critical'
    elif risk_score >= 45:
        status = 'high_risk'
    elif risk_score >= 20:
        status = 'warning'
    else:
        status = 'healthy'
    
    affected = [r.sensor_id for r in readings if r.status != 'healthy']
    
    return ZoneHealth(
        zone_id=zone_id,
        zone_name=zone_name,
        risk_score=risk_score,
        status=status,
        active_incidents=active_incident_ids,
        affected_sensors=affected,
        sensor_count=len(readings),
        last_updated=now_iso()
    )

def simulate_battery(battery_base: int, tick_count: int, sensor_id: str) -> int:
    """Slowly drain battery with sensor-specific seed for variation."""
    drain_rate = 0.0001  # ~1% per ~10000 ticks (~2.7 hours)
    # Add some random variation seeded by sensor_id to avoid all draining at same rate
    seed_offset = sum(ord(c) for c in sensor_id) % 20
    drained = int((tick_count + seed_offset * 100) * drain_rate)
    return max(5, battery_base - drained)

def simulate_signal(signal_base: int, tick_count: int) -> int:
    """Signal fluctuates slightly around base with occasional dips."""
    # Slow sinusoidal variation ±5
    variation = int(5 * math.sin(tick_count * 0.003))
    noise = random.randint(-2, 2)
    return max(10, min(99, signal_base + variation + noise))
