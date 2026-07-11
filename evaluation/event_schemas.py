"""
Event schema contracts.

Every event type that crosses a module boundary in this project (simulator
-> enrichment worker, CV pipeline -> enrichment worker, any of the above ->
Member 1's ingest endpoint) is defined here as a minimal required-field
contract. This exists specifically to catch the class of bug the Module 6
checklist calls out -- "event-shape mismatches between simulator/CV output
and the shared schemas" -- BEFORE integration day, by validating every
event *this* member's code actually emits against the shape everything
downstream assumes.

Deliberately NOT a heavyweight validation library dependency (pydantic/
jsonschema) -- this needs to be trivially readable by Member 1 as the
source of truth for "what am I receiving," so it's plain dicts + a small
checker function.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type


@dataclass
class FieldSpec:
    name: str
    type: Type
    required: bool = True
    validator: Optional[Callable[[Any], bool]] = None  # extra semantic check beyond type


EVENT_SCHEMAS: Dict[str, List[FieldSpec]] = {
    "sensor_reading": [
        FieldSpec("event_type", str),
        FieldSpec("zone_id", str),
        FieldSpec("sensor_type", str, validator=lambda v: v in
                   {"gas_ppm", "temp_c", "pressure_kpa", "vibration_mm_s"}),
        FieldSpec("value", (int, float)),
        FieldSpec("sim_time_s", (int, float)),
        FieldSpec("timestamp", str),
    ],
    "permit_issued": [
        FieldSpec("event_type", str),
        FieldSpec("zone_id", str),
        FieldSpec("permit_id", str),
        FieldSpec("permit_type", str),
        FieldSpec("sim_time_s", (int, float)),
    ],
    "permit_closed": [
        FieldSpec("event_type", str),
        FieldSpec("permit_id", str),
        FieldSpec("sim_time_s", (int, float)),
        FieldSpec("zone_id", str, required=False),  # tolerated missing -- permit_id is the real key
    ],
    "shift_boundary": [
        FieldSpec("event_type", str),
        FieldSpec("outgoing_shift", str),
        FieldSpec("incoming_shift", str),
        FieldSpec("sim_time_s", (int, float)),
    ],
    "changeover_window_start": [
        FieldSpec("event_type", str),
        FieldSpec("outgoing_shift", str),
        FieldSpec("incoming_shift", str),
        FieldSpec("sim_time_s", (int, float)),
    ],
    "cv_detection": [
        FieldSpec("event_type", str),
        FieldSpec("zone_id", str),
        FieldSpec("sim_time_s", (int, float)),
        FieldSpec("worker_count", int),
        FieldSpec("ppe_violation", bool),
        FieldSpec("confidence", (int, float)),
    ],
    "cv_zone_occupancy": [
        FieldSpec("event_type", str),
        FieldSpec("zone_id", str),
        FieldSpec("sim_time_s", (int, float)),
        FieldSpec("occupancy_count", int),
    ],
}


class SchemaViolation(Exception):
    def __init__(self, event_type: str, errors: List[str]):
        self.event_type = event_type
        self.errors = errors
        super().__init__(f"Schema violation for '{event_type}': {'; '.join(errors)}")


def validate_event(event: dict, raise_on_error: bool = True) -> List[str]:
    """
    Validates `event` against EVENT_SCHEMAS[event["event_type"]]. Returns a
    list of human-readable error strings (empty list = valid). Raises
    SchemaViolation if raise_on_error and there are any errors.
    """
    event_type = event.get("event_type")
    errors = []

    if event_type is None:
        errors.append("missing 'event_type' field entirely")
        if raise_on_error:
            raise SchemaViolation("<unknown>", errors)
        return errors

    schema = EVENT_SCHEMAS.get(event_type)
    if schema is None:
        errors.append(f"unknown event_type '{event_type}' -- not in EVENT_SCHEMAS "
                       f"(known: {sorted(EVENT_SCHEMAS)})")
        if raise_on_error:
            raise SchemaViolation(event_type, errors)
        return errors

    for field in schema:
        if field.name not in event:
            if field.required:
                errors.append(f"missing required field '{field.name}'")
            continue
        value = event[field.name]
        if not isinstance(value, field.type):
            errors.append(f"field '{field.name}' expected type {field.type}, got {type(value)}")
            continue
        if field.validator is not None and not field.validator(value):
            errors.append(f"field '{field.name}' failed semantic validation (value={value!r})")

    if errors and raise_on_error:
        raise SchemaViolation(event_type, errors)
    return errors


def validate_stream(events: List[dict]) -> Dict[str, List[str]]:
    """Validates a batch of events; returns {event_index_or_type: [errors]} for any that fail."""
    failures = {}
    for i, ev in enumerate(events):
        errs = validate_event(ev, raise_on_error=False)
        if errs:
            failures[f"event[{i}] ({ev.get('event_type', '?')})"] = errs
    return failures
