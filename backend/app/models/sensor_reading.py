from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Double
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SensorReading(Base):
    """Time-series sensor readings — backed by a TimescaleDB hypertable."""

    __tablename__ = "sensor_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    reading_value: Mapped[float] = mapped_column(Double, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        server_default=func.now(),
        nullable=False,
    )
    # TimescaleDB hypertable is created via migration on `recorded_at`
