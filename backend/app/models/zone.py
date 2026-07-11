from __future__ import annotations

import uuid
from sqlalchemy import String, CheckConstraint, ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Zone(Base):
    """Industrial plant zones — the primary spatial unit of risk tracking."""

    __tablename__ = "zones"
    __table_args__ = (
        CheckConstraint(
            "hazard_class IN ('gas', 'thermal', 'mechanical', 'confined_space', 'general')",
            name="ck_zones_hazard_class",
        ),
    )

    plant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hazard_class: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    polygon_geojson: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    current_risk_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    slug: Mapped[str] = mapped_column(String(100), nullable=True, unique=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
