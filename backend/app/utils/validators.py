from __future__ import annotations

import uuid
from datetime import datetime


def validate_uuid(value: str) -> uuid.UUID:
    """Parse and validate a UUID string; raises ValueError on failure."""
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid UUID: {value}") from exc


def validate_date_range(valid_from: datetime, valid_to: datetime) -> None:
    """Ensure valid_from < valid_to; raises ValueError otherwise."""
    if valid_from >= valid_to:
        raise ValueError(f"valid_from ({valid_from}) must be before valid_to ({valid_to})")


def clamp(value: float | int, lo: float | int, hi: float | int) -> float | int:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))


def sanitize_string(value: str, max_length: int = 500) -> str:
    """Strip whitespace and truncate to max_length."""
    return value.strip()[:max_length]
