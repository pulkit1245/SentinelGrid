from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from backend.app.simulator.models import SensorConfig, SensorReading, IncidentPhase
from backend.app.simulator.utils import compute_status, simulate_battery, simulate_signal, now_iso


@dataclass
class IncidentEffect:
    """Tracks an active incident's effect on a sensor."""
    incident_id: str
    incident_type: str
    peak_delta: float          # Max deviation from base (positive or negative)
    escalation_seconds: float  # Time to reach ~peak
    peak_hold_seconds: float   # How long to hold near peak
    recovery_seconds: float    # Time to return to baseline
    phase: IncidentPhase = IncidentPhase.ESCALATING
    elapsed: float = 0.0
    current_delta: float = 0.0
    peak_reached: float = 0.0  # Actual peak delta value when peak_hold starts

    def tick(self, dt: float = 1.0) -> float:
        """Advance time and return current incident delta value."""
        self.elapsed += dt

        if self.phase == IncidentPhase.ESCALATING:
            # Sigmoid escalation: f(t) = peak / (1 + exp(-k*(t - t_mid)))
            # k controls steepness, t_mid is midpoint of escalation curve
            k = 12.0 / self.escalation_seconds  # steepness
            t_mid = self.escalation_seconds * 0.5
            self.current_delta = self.peak_delta / (1 + math.exp(-k * (self.elapsed - t_mid)))

            if self.elapsed >= self.escalation_seconds:
                self.phase = IncidentPhase.PEAK
                self.peak_reached = self.current_delta
                self.elapsed = 0.0

        elif self.phase == IncidentPhase.PEAK:
            # Hold at peak with tiny fluctuation
            noise = random.gauss(0, abs(self.peak_delta) * 0.02)
            self.current_delta = self.peak_reached + noise

            if self.elapsed >= self.peak_hold_seconds:
                self.phase = IncidentPhase.RECOVERING
                self.elapsed = 0.0

        elif self.phase == IncidentPhase.RECOVERING:
            # Exponential decay: f(t) = peak * exp(-3 * t / recovery_seconds)
            self.current_delta = self.peak_reached * math.exp(-3.0 * self.elapsed / self.recovery_seconds)

            if self.elapsed >= self.recovery_seconds:
                self.phase = IncidentPhase.RESOLVED
                self.current_delta = 0.0

        elif self.phase == IncidentPhase.RESOLVED:
            self.current_delta = 0.0

        return self.current_delta

    @property
    def is_resolved(self) -> bool:
        return self.phase == IncidentPhase.RESOLVED


class SensorEngine:
    """Physics-based sensor simulator using Ornstein-Uhlenbeck process.
    
    Models realistic sensor behavior:
    - Natural drift around equilibrium (OU process)
    - Incident-driven escalation (sigmoid curve)
    - Gradual recovery (exponential decay)
    - Battery drain and signal variation
    """

    def __init__(self, config: SensorConfig) -> None:
        self.config = config
        self.value: float = config.base_value
        self.theta: float = 0.08   # Mean reversion speed
        self.sigma: float = config.noise_std
        self.mu: float = config.base_value  # Equilibrium
        self.offline: bool = False
        self.offline_remaining: float = 0.0
        self._incidents: list[IncidentEffect] = []
        self._tick_count: int = 0

    def add_incident(self, effect: IncidentEffect) -> None:
        # Remove any existing incident of same type to avoid stacking
        self._incidents = [i for i in self._incidents if i.incident_type != effect.incident_type]
        self._incidents.append(effect)

    def set_offline(self, duration_seconds: float) -> None:
        self.offline = True
        self.offline_remaining = duration_seconds

    def reset(self) -> None:
        """Clear all incidents and return to baseline."""
        self._incidents.clear()
        self.offline = False
        self.offline_remaining = 0.0
        self.value = self.config.base_value

    def tick(self, dt: float = 1.0) -> SensorReading:
        self._tick_count += 1
        cfg = self.config

        # Handle offline state
        if self.offline:
            self.offline_remaining -= dt
            if self.offline_remaining <= 0:
                self.offline = False
            return SensorReading(
                sensor_id=cfg.id,
                sensor_name=cfg.name,
                sensor_type=cfg.sensor_type,
                zone_id=cfg.zone_id,
                zone_name=cfg.zone_name,
                x=cfg.x, y=cfg.y,
                current_value=round(self.value, 2),
                unit=cfg.unit,
                status='offline',
                threshold_warning=cfg.threshold_warning,
                threshold_high=cfg.threshold_high,
                threshold_critical=cfg.threshold_critical,
                battery_level=simulate_battery(cfg.battery_base, self._tick_count, cfg.id),
                signal_strength=0,
                last_updated=now_iso(),
                incident_active=False,
                incident_type=None,
            )

        # ── Ornstein-Uhlenbeck natural drift ─────────────────────────────────
        dW = random.gauss(0, 1) * math.sqrt(dt)
        drift = self.theta * (self.mu - self.value) * dt
        diffusion = self.sigma * dW
        self.value += drift + diffusion

        # ── Incident effects ──────────────────────────────────────────────────
        total_incident_delta = 0.0
        active_type: Optional[str] = None
        resolved = []
        for inc in self._incidents:
            delta = inc.tick(dt)
            total_incident_delta += delta
            if inc.is_resolved:
                resolved.append(inc)
            else:
                active_type = inc.incident_type
        for r in resolved:
            self._incidents.remove(r)

        # Clamp value to physically plausible range (no negatives for most sensors)
        effective_value = self.value + total_incident_delta
        if cfg.sensor_type not in ('temperature',):  # temp can't go below 0
            effective_value = max(0.0, effective_value)
        effective_value = max(0.0, effective_value)  # All values >= 0

        status = compute_status(
            effective_value,
            cfg.threshold_warning,
            cfg.threshold_high,
            cfg.threshold_critical,
        )

        return SensorReading(
            sensor_id=cfg.id,
            sensor_name=cfg.name,
            sensor_type=cfg.sensor_type,
            zone_id=cfg.zone_id,
            zone_name=cfg.zone_name,
            x=cfg.x, y=cfg.y,
            current_value=round(effective_value, 2),
            unit=cfg.unit,
            status=status,
            threshold_warning=cfg.threshold_warning,
            threshold_high=cfg.threshold_high,
            threshold_critical=cfg.threshold_critical,
            battery_level=simulate_battery(cfg.battery_base, self._tick_count, cfg.id),
            signal_strength=simulate_signal(cfg.signal_base, self._tick_count),
            last_updated=now_iso(),
            incident_active=bool(self._incidents),
            incident_type=active_type,
        )
