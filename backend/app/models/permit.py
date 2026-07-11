from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import String, CheckConstraint, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Permit(Base):
    """Permit-to-work records."""

    __tablename__ = "permits"
    __table_args__ = (
        CheckConstraint(
            "permit_type IN ('hot_work', 'confined_space', 'excavation', 'electrical')",
            name="ck_permits_permit_type",
        ),
        CheckConstraint(
            "status IN ('active', 'closed', 'revoked')",
            name="ck_permits_status",
        ),
    )

    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permit_type: Mapped[str] = mapped_column(String(30), nullable=False)
    issued_to_worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True
    )
    issued_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)
