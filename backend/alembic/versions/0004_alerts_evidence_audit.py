"""Create alerts, evidence_snapshots, audit_logs tables

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-15 00:03:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # alerts
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("zone_id", UUID(as_uuid=True), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("graph_path", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "severity IN ('info', 'watch', 'warning', 'critical')",
            name="ck_alerts_severity",
        ),
    )
    op.create_index("ix_alerts_zone_id", "alerts", ["zone_id"])
    op.create_index("ix_alerts_triggered_at", "alerts", ["triggered_at"])
    op.create_index("ix_alerts_is_active", "alerts", ["is_active"])

    # evidence_snapshots — immutable (no UPDATE grant)
    op.create_table(
        "evidence_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alert_id", UUID(as_uuid=True), sa.ForeignKey("alerts.id"), nullable=False, unique=True),
        sa.Column("snapshot_data", JSONB, nullable=True),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column("s3_bucket", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_evidence_snapshots_alert_id", "evidence_snapshots", ["alert_id"])

    # Revoke UPDATE on evidence_snapshots for forensic integrity (production role only)
    from sqlalchemy import text

    conn = op.get_bind()
    has_role = conn.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = 'sentinelgrid'")
    ).fetchone()
    if has_role:
        op.execute("REVOKE UPDATE ON evidence_snapshots FROM sentinelgrid")

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("evidence_snapshots")
    op.drop_table("alerts")
