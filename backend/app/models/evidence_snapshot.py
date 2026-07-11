from __future__ import annotations

import uuid
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EvidenceSnapshot(Base):
    """Immutable forensic evidence snapshots for confirmed alerts.

    DB-level: no UPDATE grant is given on this table (see migration 0004).
    Once written, a snapshot cannot be modified — only read.
    """

    __tablename__ = "evidence_snapshots"
    __table_args__ = (
        UniqueConstraint("alert_id", name="uq_evidence_snapshots_alert_id"),
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False, index=True
    )
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=True)
    s3_bucket: Mapped[str] = mapped_column(String(200), nullable=True)
