"""Redis client helpers — use RESP2 for compatibility with Redis 3.x on Windows."""

from __future__ import annotations

import redis
import redis.asyncio as aioredis

from app.core.config import settings

# Redis 3.x (e.g. Redis on Windows) does not support the RESP3 HELLO handshake.
_REDIS_KWARGS = {"protocol": 2}


def get_sync_redis(**kwargs) -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, **_REDIS_KWARGS, **kwargs)


def get_async_redis(**kwargs) -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, **_REDIS_KWARGS, **kwargs)
