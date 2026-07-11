from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class SensorIngestRequest(BaseModel):
    sensor_id: uuid.UUID
    zone_id: uuid.UUID
    sensor_type: Literal["gas", "temperature", "pressure", "vibration"]
    value: float
    unit: str
    recorded_at: datetime


class SensorResponse(BaseModel):
    id: uuid.UUID
    zone_id: uuid.UUID
    name: str
    sensor_type: str
    unit: str
    is_active: bool
    statutory_threshold: float | None = None
    warning_threshold: float | None = None

    class Config:
        from_attributes = True


class SensorReadingResponse(BaseModel):
    sensor_id: uuid.UUID
    reading_value: float
    recorded_at: datetime

    class Config:
        from_attributes = True
