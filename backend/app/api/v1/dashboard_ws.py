from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.middlewares.auth_middleware import get_ws_user_from_token

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Connection Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WS client connected", extra={"total": len(self._connections)})

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WS client disconnected", extra={"total": len(self._connections)})

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast JSON to all connected clients; silently drop dead connections."""
        payload = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)

    async def send_personal(self, ws: WebSocket, message: dict[str, Any]) -> None:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            self._connections.discard(ws)


manager = ConnectionManager()


async def _heartbeat(ws: WebSocket) -> None:
    """Send a heartbeat ping every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        try:
            await ws.send_text(
                json.dumps(
                    {
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": {"server_time": datetime.now(timezone.utc).isoformat()},
                    }
                )
            )
        except Exception:
            break


# ── WebSocket Endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket, token: str = ""):
    """Live dashboard WebSocket.

    Query param: ?token=<JWT access token>
    Closes with 4401 if token is invalid.
    Broadcasts: zone_risk_update | new_alert | alert_confirmed | permit_created | permit_revoked | cv_event | heartbeat
    """
    # Validate JWT from query param
    try:
        user = await get_ws_user_from_token(token)
    except Exception:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await manager.connect(websocket)

    # Send initial welcome message
    await manager.send_personal(
        websocket,
        {
            "type": "heartbeat",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "server_time": datetime.now(timezone.utc).isoformat(),
                "user_role": user.role,
            },
        },
    )

    heartbeat_task = asyncio.create_task(_heartbeat(websocket))

    try:
        while True:
            # Keep connection alive; agents/services call broadcast() directly
            data = await websocket.receive_text()
            # Clients may send ping messages — just echo back
            if data == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        manager.disconnect(websocket)


async def broadcast_event(event_type: str, payload: dict[str, Any]) -> None:
    """Helper for other modules to push events to all cockpit clients."""
    await manager.broadcast(
        {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
    )
