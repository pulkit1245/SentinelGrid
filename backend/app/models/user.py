from __future__ import annotations

import uuid
from sqlalchemy import String, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class User(Base):
    """System users: safety officers, plant admins, auditors."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('safety_officer', 'plant_admin', 'auditor')",
            name="ck_users_role",
        ),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="safety_officer"
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
