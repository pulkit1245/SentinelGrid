from __future__ import annotations

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://sentinelgrid:password@localhost:5433/sentinelgrid"
    DATABASE_SYNC_URL: str = "postgresql://sentinelgrid:password@localhost:5433/sentinelgrid"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Neo4j ─────────────────────────────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ── Qdrant ────────────────────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_PATH: str = ""

    # ── Auth ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Service Auth ──────────────────────────────────────────────────────────
    SERVICE_TOKEN: str = "dev-service-token"

    # ── Twilio ────────────────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    ALERT_PHONE_NUMBERS: List[str] = []   # comma-separated in .env

    # ── Mapbox ────────────────────────────────────────────────────────────────
    MAPBOX_TOKEN: str = ""

    # ── LLM ───────────────────────────────────────────────────────────────────
    LLM_API_KEY: str = ""

    # ── Object Storage ────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "sentinelgrid-evidence"

    # ── Monitoring ────────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
