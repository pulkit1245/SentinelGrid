from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

try:
    import sentry_sdk
except ImportError:  # pragma: no cover
    sentry_sdk = None  # type: ignore[assignment]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging
from app.middlewares.error_handler import register_error_handlers

# Import all routers
from app.api.v1 import auth, zones, sensors, permits, alerts, compliance, rag, graph, dashboard_ws, events

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    configure_logging()
    logger.info("SentinelGrid backend starting up", extra={"environment": settings.ENVIRONMENT})

    if sentry_sdk and settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.2)
        logger.info("Sentry initialized")

    yield

    logger.info("SentinelGrid backend shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SentinelGrid API",
        description="Compound-Risk Detection & Autonomous Response Platform for Industrial Safety",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    )

    # ── CORS ────────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Error Handlers ─────────────────────────────────────────────────────────
    register_error_handlers(app)

    # ── Routes ─────────────────────────────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(auth.router, prefix=prefix, tags=["auth"])
    app.include_router(zones.router, prefix=prefix, tags=["zones"])
    app.include_router(sensors.router, prefix=prefix, tags=["sensors"])
    app.include_router(permits.router, prefix=prefix, tags=["permits"])
    app.include_router(alerts.router, prefix=prefix, tags=["alerts"])
    app.include_router(compliance.router, prefix=prefix, tags=["compliance"])
    app.include_router(rag.router, prefix=prefix, tags=["rag"])
    app.include_router(graph.router, prefix=prefix, tags=["graph"])
    app.include_router(events.router, prefix=prefix, tags=["events"])
    app.include_router(dashboard_ws.router, tags=["websocket"])

    # ── Health Check ───────────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health_check() -> JSONResponse:
        from datetime import datetime, timezone
        return JSONResponse({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

    return app


app = create_app()
