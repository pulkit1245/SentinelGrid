from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel


class AlertCreate(BaseModel):
    zone_id: uuid.UUID
    severity: Literal["info", "watch", "warning", "critical"]
    title: str
    description: str | None = None
    graph_path: list[dict[str, Any]] = []


class AlertResponse(BaseModel):
    id: uuid.UUID
    zone_id: uuid.UUID
    severity: str
    title: str
    description: str | None = None
    graph_path: list[dict[str, Any]]
    triggered_at: datetime
    confirmed_by: uuid.UUID | None = None
    confirmed_at: datetime | None = None
    is_active: bool

    class Config:
        from_attributes = True


class AlertConfirmResponse(BaseModel):
    id: uuid.UUID
    confirmed_by: uuid.UUID
    confirmed_at: datetime
    message: str = "Alert confirmed. Evacuation notification dispatched."
