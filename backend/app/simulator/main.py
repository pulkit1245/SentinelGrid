"""
main.py — Standalone FastAPI application for the SentinelGrid Sensor Simulator.

Run with:
    cd /path/to/SentinelGrid
    PYTHONPATH=$(pwd) backend/.venv/bin/uvicorn backend.app.simulator.main:app \\
        --port 8002 --reload

Environment variables:
    BRIDGE_URL          URL of backend batch endpoint (default: http://localhost:8000/api/v1/simulator/batch)
    SERVICE_TOKEN       Service auth token (must match backend SERVICE_TOKEN)
    SIMULATOR_CONFIG_DIR  Path to simulator/config/ directory
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.simulator.routes import router
from backend.app.simulator.scheduler import SimulatorScheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ── Startup ────────────────────────────────────────────────────────────────
    bridge_url = os.environ.get("BRIDGE_URL", "http://localhost:8000/api/v1/simulator/batch")
    service_token = os.environ.get("SERVICE_TOKEN", "internal-service-token-change-in-production")

    scheduler = SimulatorScheduler(bridge_url=bridge_url, service_token=service_token)
    app.state.scheduler = scheduler
    await scheduler.start()
    logger.info("SentinelGrid Simulator started — %d sensors loaded", len(scheduler.engines))

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    await scheduler.stop()
    logger.info("SentinelGrid Simulator stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SentinelGrid Sensor Simulator",
        description=(
            "Physics-based industrial sensor simulator for SentinelGrid SCADA platform. "
            "Streams realistic telemetry via the backend bridge WebSocket pipeline. "
            "Provides REST control API for manual incident triggering."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],    # Simulator is internal — open CORS
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Include control routes ─────────────────────────────────────────────────
    app.include_router(router, tags=["simulator"])

    # ── Root health check ──────────────────────────────────────────────────────
    @app.get("/", tags=["health"])
    async def root() -> JSONResponse:
        return JSONResponse({
            "service": "SentinelGrid Sensor Simulator",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "endpoints": {
                "status": "/status",
                "sensors": "/sensors",
                "zone_health": "/zones/health",
                "incidents": "/incidents",
                "trigger_gas_leak": "POST /simulate/gas-leak",
                "trigger_fire": "POST /simulate/fire",
                "reset": "POST /simulate/reset",
            }
        })

    return app


app = create_app()
