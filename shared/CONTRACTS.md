# SentinelGrid Shared Contracts

This document defines the JSON schemas for the core data models that all agents, the backend, and the frontend will use to communicate.
These schemas are the source of truth.

## Zone
```json
{
  "id": "uuid",
  "name": "string",
  "hazard_class": "enum(gas, thermal, mechanical, confined_space, general)",
  "current_risk_score": "integer(0-100)"
}
```

## Sensor Reading Event
```json
{
  "sensor_id": "uuid",
  "zone_id": "uuid",
  "sensor_type": "enum(gas, temperature, pressure, vibration)",
  "reading_value": "float",
  "recorded_at": "iso8601_timestamp"
}
```

## Permit Event
```json
{
  "id": "uuid",
  "zone_id": "uuid",
  "permit_type": "enum(hot_work, confined_space, excavation, electrical)",
  "status": "enum(active, closed, revoked)",
  "valid_from": "iso8601_timestamp",
  "valid_to": "iso8601_timestamp"
}
```

## Alert
```json
{
  "id": "uuid",
  "zone_id": "uuid",
  "severity": "enum(info, watch, warning, critical)",
  "graph_path": "object (visual lineage)",
  "triggered_at": "iso8601_timestamp"
}
```
