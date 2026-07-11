from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Equipment(Base):
    """Plant equipment tracked in the risk graph."""

    __tablename__ = "equipment"

    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=True)
    maintained_by_worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True
    )
    last_maintenance_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    maintenance_interval_days: Mapped[int] = mapped_column(nullable=True)
    is_overdue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=True)
