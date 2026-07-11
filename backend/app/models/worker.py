from __future__ import annotations

import uuid
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Worker(Base):
    """Plant workers associated with permits and zones."""

    __tablename__ = "workers"

    plant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    badge_id: Mapped[str] = mapped_column(String(50), nullable=True, unique=True)
    role: Mapped[str] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=True)
    is_on_shift: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
