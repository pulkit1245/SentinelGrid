from __future__ import annotations

"""Time alignment utilities for the enrichment worker.

NOTE: Full implementation owned by Member 2 (backend/app/workers/tasks/enrichment_task.py).
This module provides the stub/interface so Member 1's ingestion service can import it.
"""


def bucket_to_grid(timestamp_iso: str, bucket_seconds: int = 60) -> str:
    """Round a timestamp down to the nearest bucket boundary.

    Args:
        timestamp_iso: ISO 8601 timestamp string.
        bucket_seconds: Bucket size in seconds (default 60s = 1-minute grid).

    Returns:
        ISO 8601 timestamp of the bucket start.
    """
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
    bucket_start = dt.timestamp() - (dt.timestamp() % bucket_seconds)
    return datetime.fromtimestamp(bucket_start, tz=timezone.utc).isoformat()


def compute_trend_slope(values: list[float], timestamps: list[float]) -> float:
    """Simple linear regression slope for a list of (value, unix_timestamp) pairs.

    Returns the slope in units/second. Positive = increasing trend.
    """
    if len(values) < 2:
        return 0.0

    n = len(values)
    sum_x = sum(timestamps)
    sum_y = sum(values)
    sum_xy = sum(x * y for x, y in zip(timestamps, values))
    sum_x2 = sum(x ** 2 for x in timestamps)

    denom = n * sum_x2 - sum_x ** 2
    if denom == 0:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom
