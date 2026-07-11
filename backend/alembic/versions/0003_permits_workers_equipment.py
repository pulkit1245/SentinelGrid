"""Create permits and equipment tables

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-15 00:02:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # permits
    op.create_table(
        "permits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("zone_id", UUID(as_uuid=True), sa.ForeignKey("zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permit_type", sa.String(30), nullable=False),
        sa.Column("issued_to_worker_id", UUID(as_uuid=True), sa.ForeignKey("workers.id"), nullable=True),
        sa.Column("issued_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "permit_type IN ('hot_work', 'confined_space', 'excavation', 'electrical')",
            name="ck_permits_permit_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'closed', 'revoked')",
            name="ck_permits_status",
        ),
    )
    op.create_index("ix_permits_zone_id", "permits", ["zone_id"])
    op.create_index("ix_permits_status", "permits", ["status"])

    # equipment
    op.create_table(
        "equipment",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("zone_id", UUID(as_uuid=True), sa.ForeignKey("zones.id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("equipment_type", sa.String(100), nullable=True),
        sa.Column("maintained_by_worker_id", UUID(as_uuid=True), sa.ForeignKey("workers.id"), nullable=True),
        sa.Column("last_maintenance_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("maintenance_interval_days", sa.Integer, nullable=True),
        sa.Column("is_overdue", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("serial_number", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("equipment")
    op.drop_table("permits")
