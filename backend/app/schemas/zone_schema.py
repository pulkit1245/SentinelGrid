from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel


class ZoneResponse(BaseModel):
    id: uuid.UUID
    plant_id: uuid.UUID
    name: str
    hazard_class: str
    polygon_geojson: dict[str, Any] | None = None
    current_risk_score: int
    active_permit_count: int = 0
    active_alert_count: int = 0
    slug: str | None = None

    class Config:
        from_attributes = True


class ZoneCreate(BaseModel):
    plant_id: uuid.UUID
    name: str
    hazard_class: str
    polygon_geojson: dict[str, Any] | None = None
    description: str | None = None


class ZoneRiskUpdate(BaseModel):
    risk_score: int


class ZoneList(BaseModel):
    zones: list[ZoneResponse]
    total: int
