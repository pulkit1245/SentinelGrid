from __future__ import annotations

import logging
import uuid

from app.core.redis_client import get_async_redis
from app.repositories.zone_repository import ZoneRepository

logger = logging.getLogger(__name__)

ZONE_RISK_CACHE_PREFIX = "sentinelgrid:zone_risk:"


class RiskScoringService:
    """Updates zone risk scores in the DB and caches in Redis."""

    def __init__(self, zone_repo: ZoneRepository) -> None:
        self.zone_repo = zone_repo

    async def update_zone_risk_score(self, zone_id: uuid.UUID, score: int) -> dict:
        # Clamp to 0-100
        score = max(0, min(100, score))

        zone = await self.zone_repo.update_zone_risk_score(zone_id, score)
        if not zone:
            raise ValueError(f"Zone {zone_id} not found")

        # Cache in Redis (TTL 90 seconds — rolling updates keep it fresh)
        try:
            r = get_async_redis(decode_responses=True)
            await r.setex(f"{ZONE_RISK_CACHE_PREFIX}{zone_id}", 90, str(score))
            await r.aclose()
        except Exception as exc:
            logger.warning("Redis cache update failed", extra={"error": str(exc)})

        logger.info("Zone risk score updated", extra={"zone_id": str(zone_id), "score": score})
        return {"zone_id": str(zone_id), "risk_score": score}

    async def get_cached_risk_score(self, zone_id: uuid.UUID) -> int | None:
        try:
            r = get_async_redis(decode_responses=True)
            val = await r.get(f"{ZONE_RISK_CACHE_PREFIX}{zone_id}")
            await r.aclose()
            return int(val) if val is not None else None
        except Exception:
            return None
