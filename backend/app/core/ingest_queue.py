"""Ingest queue helpers — Redis Streams with list fallback for Redis 3.x on Windows."""

from __future__ import annotations

import json
import logging

from app.core.redis_client import get_async_redis, get_sync_redis

logger = logging.getLogger(__name__)

INGEST_STREAM_KEY = "sentinelgrid:ingest"
INGEST_LIST_KEY = "sentinelgrid:ingest:list"
DEAD_LETTER_STREAM_KEY = "sentinelgrid:ingest:dead_letter"
DEAD_LETTER_LIST_KEY = "sentinelgrid:ingest:dead_letter:list"


def streams_supported(redis_client) -> bool:
    try:
        redis_client.execute_command("XINFO", "HELP")
        return True
    except Exception:
        return False


async def publish_ingest_event(event: dict) -> None:
    payload = json.dumps(event)
    r = get_async_redis(decode_responses=True)
    try:
        await r.xadd(
            INGEST_STREAM_KEY,
            {"payload": payload},
            maxlen=10_000,
            approximate=True,
        )
    except Exception as exc:
        logger.warning(
            "Redis stream publish failed — using list fallback",
            extra={"error": str(exc)},
        )
        await r.lpush(INGEST_LIST_KEY, payload)
    finally:
        await r.aclose()


def publish_ingest_event_sync(event: dict, redis_client=None) -> None:
    payload = json.dumps(event)
    r = redis_client or get_sync_redis(decode_responses=True)
    close = redis_client is None
    try:
        r.xadd(
            INGEST_STREAM_KEY,
            {"payload": payload},
            maxlen=10_000,
            approximate=True,
        )
    except Exception as exc:
        logger.warning(
            "Redis stream publish failed — using list fallback",
            extra={"error": str(exc)},
        )
        r.lpush(INGEST_LIST_KEY, payload)
    finally:
        if close:
            r.close()
