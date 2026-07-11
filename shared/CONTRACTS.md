# SentinelGrid — Shared API & Event Contracts

> **This document is the single source of truth for all inter-service event schemas and API object shapes.**  
> All three team members code against these contracts. Field names are **frozen** once committed to `main`.

---

## 1. Sensor Reading Event

Posted by the simulator (Member 2) to `POST /api/v1/sensors/ingest`.  
Also published to the `sentinelgrid:sensor_readings` Redis Stream.

```json
{
  "sensor_id": "uuid-v4",
  "zone_id": "uuid-v4",
  "sensor_type": "gas | temperature | pressure | vibration",
  "value": 42.7,
  "unit": "ppm | celsius | bar | mm/s",
  "recorded_at": "2025-01-15T10:30:00Z"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `sensor_id` | UUID string | ✅ | Must exist in DB |
| `zone_id` | UUID string | ✅ | Must exist in DB |
| `sensor_type` | enum | ✅ | `gas`, `temperature`, `pressure`, `vibration` |
| `value` | float | ✅ | Raw reading in the sensor's native unit |
| `unit` | string | ✅ | SI unit string |
| `recorded_at` | ISO 8601 UTC | ✅ | When the reading was taken at the sensor |

---

## 2. Permit Event

Emitted when a permit is created/revoked. Also published to `sentinelgrid:permit_events` Redis Stream.

```json
{
  "event_type": "permit_created | permit_revoked | permit_expired",
  "permit_id": "uuid-v4",
  "zone_id": "uuid-v4",
  "permit_type": "hot_work | confined_space | excavation | electrical",
  "issued_to_worker_id": "uuid-v4",
  "valid_from": "2025-01-15T08:00:00Z",
  "valid_to": "2025-01-15T16:00:00Z",
  "status": "active | closed | revoked",
  "timestamp": "2025-01-15T08:00:00Z"
}
```

---

## 3. Alert Object

Returned by `GET /api/v1/alerts/{alert_id}`. Also pushed over WebSocket.

```json
{
  "id": "uuid-v4",
  "zone_id": "uuid-v4",
  "zone_name": "Zone 01 — Degassing Unit",
  "severity": "info | watch | warning | critical",
  "title": "Compound Risk: Hot-Work + Elevated Gas",
  "description": "Hot-work permit active while gas readings trending upward near shift changeover.",
  "graph_path": [
    {"node": "Permit:hot_work", "rel": "OVERLAPS_WITH", "next": "Zone:01"},
    {"node": "Zone:01", "rel": "HAS_SENSOR", "next": "Sensor:gas-A1"},
    {"node": "Sensor:gas-A1", "rel": "TRENDING_UP", "value": 42.7, "threshold": 50.0}
  ],
  "triggered_at": "2025-01-15T10:32:00Z",
  "confirmed_by": null,
  "confirmed_at": null,
  "is_active": true,
  "evidence_snapshot_id": null
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `zone_id` | UUID | FK |
| `severity` | enum | `info`, `watch`, `warning`, `critical` |
| `graph_path` | array | Causal chain — the "why" shown to the officer |
| `confirmed_by` | UUID or null | Set when a `plant_admin` confirms |
| `confirmed_at` | ISO8601 or null | Timestamp of human confirmation |
| `is_active` | bool | False once closed/resolved |

---

## 4. Zone Object

Returned by `GET /api/v1/zones` and `GET /api/v1/zones/{zone_id}`.  
Also pushed over WebSocket when `current_risk_score` changes.

```json
{
  "id": "uuid-v4",
  "plant_id": "uuid-v4",
  "name": "Zone 01 — Degassing Unit",
  "hazard_class": "gas | thermal | mechanical | confined_space | general",
  "polygon_geojson": {
    "type": "Polygon",
    "coordinates": [[[lon, lat], [lon, lat], [lon, lat]]]
  },
  "current_risk_score": 72,
  "active_permit_count": 2,
  "active_alert_count": 1,
  "sensors": []
}
```

---

## 5. CV Detection Event

Published by the CV pipeline (Member 2) to `sentinelgrid:cv_events` Redis Stream.

```json
{
  "zone_id": "uuid-v4",
  "event_type": "ppe_violation | zone_intrusion | occupancy_update",
  "worker_track_id": "deepsort-123",
  "worker_count": 3,
  "ppe_violation": true,
  "ppe_details": {
    "missing": ["hard_hat"],
    "present": ["vest"]
  },
  "confidence": 0.91,
  "frame_timestamp": "2025-01-15T10:30:00.500Z",
  "snapshot_s3_key": "cv/zone-01/2025-01-15/frame-abc123.jpg"
}
```

---

## 6. WebSocket Message Envelope

All messages pushed over `ws://host/ws/dashboard` use this envelope.

```json
{
  "type": "zone_risk_update | new_alert | alert_confirmed | permit_created | permit_revoked | cv_event | heartbeat",
  "timestamp": "2025-01-15T10:32:00Z",
  "payload": { }
}
```

- `zone_risk_update` payload: full Zone object with updated `current_risk_score`
- `new_alert` payload: full Alert object
- `alert_confirmed` payload: `{ alert_id, confirmed_by, confirmed_at }`
- `permit_created` / `permit_revoked` payload: Permit Event object
- `cv_event` payload: CV Detection Event
- `heartbeat` payload: `{ server_time }`

---

## Field Name Conventions

- All IDs: `snake_case` UUID strings (e.g. `zone_id`, not `zoneId`)
- All timestamps: ISO 8601 UTC strings ending in `Z`
- All enum values: `snake_case` lowercase
- No `null` for required fields — omit optional fields if absent rather than sending `null`
