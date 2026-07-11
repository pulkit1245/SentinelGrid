from __future__ import annotations

import uuid
from sqlalchemy import String, CheckConstraint, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Sensor(Base):
    """Physical sensors attached to zones."""

    __tablename__ = "sensors"
    __table_args__ = (
        CheckConstraint(
            "sensor_type IN ('gas', 'temperature', 'pressure', 'vibration')",
            name="ck_sensors_sensor_type",
        ),
    )

    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(30), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    statutory_threshold: Mapped[float | None] = mapped_column(nullable=True)
    warning_threshold: Mapped[float | None] = mapped_column(nullable=True)
