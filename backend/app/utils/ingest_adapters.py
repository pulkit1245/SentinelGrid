"""Adapters translating Member 2 simulator payloads into shared contract shapes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

# Stable slug → UUID mapping (must match backend/scripts/seed_demo_data.py)
ZONE_SLUG_TO_UUID: dict[str, uuid.UUID] = {
    "zone-01-degassing": uuid.UUID("10000000-0000-0000-0000-000000000001"),
    "zone-02-castfloor": uuid.UUID("10000000-0000-0000-0000-000000000002"),
    "zone-03-pump-room": uuid.UUID("10000000-0000-0000-0000-000000000003"),
    "zone-04-storage": uuid.UUID("10000000-0000-0000-0000-000000000004"),
    "zone-05-confined-tank": uuid.UUID("10000000-0000-0000-0000-000000000005"),
}

SENSOR_TYPE_MAP = {
    "gas_ppm": ("gas", "ppm"),
    "temp_c": ("temperature", "celsius"),
    "pressure_kpa": ("pressure", "kpa"),
    "vibration_mm_s": ("vibration", "mm/s"),
    "gas": ("gas", "ppm"),
    "temperature": ("temperature", "celsius"),
    "pressure": ("pressure", "bar"),
    "vibration": ("vibration", "mm/s"),
}


def resolve_zone_id(zone_ref: str) -> str:
    try:
        uuid.UUID(zone_ref)
        return zone_ref
    except ValueError:
        mapped = ZONE_SLUG_TO_UUID.get(zone_ref)
        if mapped:
            return str(mapped)
    return zone_ref


def normalize_simulator_event(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize simulator/CV event payloads for the enrichment worker."""
    normalized = dict(event)
    if "zone_id" in normalized:
        normalized["zone_id"] = resolve_zone_id(str(normalized["zone_id"]))

    et = normalized.get("event_type", "")
    if et in ("permit_created", "permit_revoked", "permit_expired"):
        mapping = {"permit_created": "permit_issued", "permit_revoked": "permit_closed", "permit_expired": "permit_closed"}
        normalized["event_type"] = mapping.get(et, et)

    if "timestamp" in normalized and "sim_time_s" not in normalized:
        try:
            ts = datetime.fromisoformat(str(normalized["timestamp"]).replace("Z", "+00:00"))
            normalized["sim_time_s"] = ts.timestamp()
        except ValueError:
            normalized["sim_time_s"] = datetime.now(timezone.utc).timestamp()

    if et == "cv_detection":
        normalized["event_type"] = "ppe_violation" if normalized.get("ppe_violation") else "occupancy_update"
        if "frame_timestamp" not in normalized and "timestamp" in normalized:
            normalized["frame_timestamp"] = normalized["timestamp"]

    return normalized


def try_normalize_sensor_ingest(payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    If payload looks like a simulator-native sensor event, return a normalized
    SensorIngestRequest-compatible dict. Otherwise return None.
    """
    if "sensor_id" in payload and "recorded_at" in payload:
        return None

    zone_slug = payload.get("zone_id")
    sensor_type_raw = payload.get("sensor_type", "gas_ppm")
    if zone_slug is None or "value" not in payload:
        return None

    sensor_type, unit = SENSOR_TYPE_MAP.get(sensor_type_raw, ("gas", "ppm"))
    zone_uuid = resolve_zone_id(str(zone_slug))

    recorded_at = payload.get("recorded_at") or payload.get("timestamp")
    if recorded_at:
        try:
            dt = datetime.fromisoformat(str(recorded_at).replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.now(timezone.utc)
    else:
        sim_time_s = payload.get("sim_time_s", 0)
        dt = datetime.fromtimestamp(float(sim_time_s), tz=timezone.utc)

    # Deterministic sensor_id per zone+type for simulator streams
    sensor_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{zone_uuid}:{sensor_type}")

    return {
        "sensor_id": sensor_id,
        "zone_id": zone_uuid,
        "sensor_type": sensor_type,
        "value": float(payload["value"]),
        "unit": unit,
        "recorded_at": dt.isoformat(),
    }
