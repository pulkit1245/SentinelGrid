from __future__ import annotations

import logging
import time
from typing import Callable

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def rate_limit(max_calls: int, window_seconds: int):
    """FastAPI dependency factory for Redis-backed rate limiting.

    Usage:
        @router.post("/auth/login", dependencies=[Depends(rate_limit(5, 60))])
    """

    async def _check(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"sentinelgrid:ratelimit:{path}:{client_ip}"

        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            pipe = r.pipeline()
            now = int(time.time())
            window_start = now - window_seconds

            # Sliding-window log approach
            await pipe.zremrangebyscore(key, 0, window_start)
            await pipe.zadd(key, {str(now): now})
            await pipe.zcard(key)
            await pipe.expire(key, window_seconds)
            results = await pipe.execute()
            await r.aclose()

            call_count = results[2]
            if call_count > max_calls:  # allows exactly max_calls attempts
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: max {max_calls} requests per {window_seconds}s. Try again in a minute.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            # If Redis is unavailable, don't block requests — log and allow
            logger.warning("Rate limiter Redis error", extra={"error": str(exc)})

    return _check
