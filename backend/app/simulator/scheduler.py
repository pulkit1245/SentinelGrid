"""
scheduler.py — Async tick loop for SentinelGrid Sensor Simulator.

Runs a 1-second async loop that:
1. Ticks all sensor engines (generates new readings via OU + incident effects)
2. Advances the incident manager
3. Computes zone health for all zones
4. POSTs a batch payload to the backend bridge endpoint
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from backend.app.simulator.config import load_sensor_configs, load_zones
from backend.app.simulator.engine import SensorEngine
from backend.app.simulator.incidents import IncidentManager
from backend.app.simulator.models import BatchPayload, SensorReading, SimulatorStatus
from backend.app.simulator.utils import compute_zone_health, now_iso

logger = logging.getLogger(__name__)

BRIDGE_URL = "http://localhost:8000/api/v1/simulator/batch"
SERVICE_TOKEN = "internal-service-token-change-in-production"
TICK_INTERVAL = 1.0  # seconds


class SimulatorScheduler:
    """
    Central async scheduler that drives the entire simulation.

    Usage:
        scheduler = SimulatorScheduler()
        await scheduler.start()        # begins background tick loop
        await scheduler.stop()         # graceful shutdown
    """

    def __init__(self, bridge_url: str = BRIDGE_URL, service_token: str = SERVICE_TOKEN) -> None:
        self.bridge_url = bridge_url
        self.service_token = service_token
        self._running = False
        self._tick_count = 0
        self._start_time: float = 0.0
        self._last_tick: str | None = None
        self._task: asyncio.Task | None = None
        self._bridge_errors = 0

        # ── Initialize engines from config ────────────────────────────────────
        sensor_configs = load_sensor_configs()
        self.engines: dict[str, SensorEngine] = {
            cfg.id: SensorEngine(cfg) for cfg in sensor_configs
        }

        # ── Build zone → sensor mapping ───────────────────────────────────────
        self.zone_configs = load_zones()
        self.zone_sensor_map: dict[str, list[str]] = {}
        for cfg in sensor_configs:
            self.zone_sensor_map.setdefault(cfg.zone_id, []).append(cfg.id)

        # ── Incident manager ──────────────────────────────────────────────────
        self.incidents = IncidentManager()
        self.incidents.register_engines(self.engines, self.zone_sensor_map)

        # ── Latest readings cache (for REST queries) ──────────────────────────
        self._latest_readings: dict[str, SensorReading] = {}

        logger.info(
            "Scheduler initialized: %d sensors across %d zones",
            len(self.engines),
            len(self.zone_configs),
        )

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_time = time.monotonic()
        self._task = asyncio.create_task(self._run(), name="simulator-tick")
        logger.info("Simulator scheduler started (bridge: %s)", self.bridge_url)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Simulator scheduler stopped after %d ticks", self._tick_count)

    # ── Main loop ──────────────────────────────────────────────────────────────

    async def _run(self) -> None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            while self._running:
                loop_start = time.monotonic()
                try:
                    await self._tick(client)
                except Exception as exc:
                    logger.warning("Tick error: %s", exc, exc_info=True)
                elapsed = time.monotonic() - loop_start
                sleep_time = max(0.0, TICK_INTERVAL - elapsed)
                await asyncio.sleep(sleep_time)

    async def _tick(self, client: httpx.AsyncClient) -> None:
        self._tick_count += 1
        self._last_tick = now_iso()

        # 1. Advance incident manager
        self.incidents.tick(dt=1.0)

        # 2. Generate readings from all engines
        readings: list[SensorReading] = []
        for sensor_id, engine in self.engines.items():
            reading = engine.tick(dt=1.0)
            readings.append(reading)
            self._latest_readings[sensor_id] = reading

        # 3. Compute zone health
        zone_health_list = []
        for zone_cfg in self.zone_configs:
            zone_id = zone_cfg["zone_id"]
            zone_readings = [r for r in readings if r.zone_id == zone_id]
            active_ids = self.incidents.active_ids_for_zone(zone_id)
            health = compute_zone_health(zone_readings, zone_id, zone_cfg["zone_name"], active_ids)
            zone_health_list.append(health)

        # 4. POST batch to bridge
        payload = BatchPayload(
            readings=readings,
            zone_health=zone_health_list,
            tick=self._tick_count,
            timestamp=self._last_tick,
        )
        await self._post_batch(client, payload)

    async def _post_batch(self, client: httpx.AsyncClient, payload: BatchPayload) -> None:
        try:
            resp = await client.post(
                self.bridge_url,
                json=payload.model_dump(),
                headers={
                    "X-Service-Token": self.service_token,
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code not in (200, 202):
                self._bridge_errors += 1
                if self._bridge_errors <= 5 or self._bridge_errors % 60 == 0:
                    logger.warning("Bridge returned %d: %s", resp.status_code, resp.text[:200])
            else:
                self._bridge_errors = 0
        except httpx.ConnectError:
            self._bridge_errors += 1
            if self._bridge_errors <= 3 or self._bridge_errors % 30 == 0:
                logger.warning("Cannot reach bridge at %s (attempt %d)", self.bridge_url, self._bridge_errors)
        except Exception as exc:
            logger.debug("Bridge post error: %s", exc)

    # ── Accessors for REST routes ──────────────────────────────────────────────

    def get_status(self) -> SimulatorStatus:
        uptime = time.monotonic() - self._start_time if self._start_time else 0.0
        return SimulatorStatus(
            running=self._running,
            tick_count=self._tick_count,
            sensor_count=len(self.engines),
            zone_count=len(self.zone_configs),
            active_incidents=len(self.incidents.all_active()),
            uptime_seconds=round(uptime, 1),
            last_tick=self._last_tick,
            bridge_url=self.bridge_url,
        )

    def get_latest_readings(self) -> list[SensorReading]:
        return list(self._latest_readings.values())

    def get_reading(self, sensor_id: str) -> SensorReading | None:
        return self._latest_readings.get(sensor_id)
