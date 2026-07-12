"""Create zones, sensors, sensor_readings tables (TimescaleDB hypertable)

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-15 00:01:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # workers table (needed as FK target for permits)
    op.create_table(
        "workers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("plant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("badge_id", sa.String(50), nullable=True, unique=True),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("is_on_shift", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # zones
    op.create_table(
        "zones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("plant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("hazard_class", sa.String(50), nullable=False, server_default="general"),
        sa.Column("polygon_geojson", JSONB, nullable=True),
        sa.Column("current_risk_score", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("slug", sa.String(100), nullable=True, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "hazard_class IN ('gas', 'thermal', 'mechanical', 'confined_space', 'general')",
            name="ck_zones_hazard_class",
        ),
    )
    op.create_index("ix_zones_plant_id", "zones", ["plant_id"])

    # sensors
    op.create_table(
        "sensors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("zone_id", UUID(as_uuid=True), sa.ForeignKey("zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("sensor_type", sa.String(30), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("statutory_threshold", sa.Double, nullable=True),
        sa.Column("warning_threshold", sa.Double, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "sensor_type IN ('gas', 'temperature', 'pressure', 'vibration')",
            name="ck_sensors_sensor_type",
        ),
    )
    op.create_index("ix_sensors_zone_id", "sensors", ["zone_id"])

    # sensor_readings (regular table first, then convert to hypertable)
    op.create_table(
        "sensor_readings",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()")),
        sa.Column("sensor_id", UUID(as_uuid=True), sa.ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", UUID(as_uuid=True), nullable=False),
        sa.Column("reading_value", sa.Double, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", "recorded_at"),
    )
    op.create_index("ix_sensor_readings_sensor_id", "sensor_readings", ["sensor_id"])
    op.create_index("ix_sensor_readings_recorded_at", "sensor_readings", ["recorded_at"])

    # Convert to TimescaleDB hypertable when extension is available (skip on plain Postgres demo)
    from sqlalchemy import text

    conn = op.get_bind()
    has_timescale = conn.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
    ).fetchone()
    if has_timescale:
        op.execute(
            "SELECT create_hypertable('sensor_readings', 'recorded_at', if_not_exists => TRUE)"
        )


def downgrade() -> None:
    op.drop_table("sensor_readings")
    op.drop_table("sensors")
    op.drop_table("zones")
    op.drop_table("workers")
