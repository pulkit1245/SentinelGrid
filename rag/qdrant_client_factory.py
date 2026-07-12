"""Qdrant client factory — server URL with local file fallback when Docker is unavailable."""

from __future__ import annotations

import os

from qdrant_client import QdrantClient


def default_local_qdrant_path() -> str:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo_root, ".local", "qdrant")


def create_qdrant_client(
    qdrant_url: str | None = None,
    qdrant_path: str | None = None,
) -> QdrantClient:
    """Prefer explicit local path; else try server URL; else use embedded local storage."""
    if qdrant_path:
        os.makedirs(qdrant_path, exist_ok=True)
        print(f"Using local Qdrant storage at {qdrant_path}")
        return QdrantClient(path=qdrant_path)

    url = qdrant_url or os.environ.get("QDRANT_URL", "http://localhost:6333")
    try:
        client = QdrantClient(url=url, timeout=5)
        client.get_collections()
        print(f"Connected to Qdrant server at {url}")
        return client
    except Exception as exc:
        local_path = os.environ.get("QDRANT_PATH") or default_local_qdrant_path()
        os.makedirs(local_path, exist_ok=True)
        print(f"Qdrant server unavailable ({exc}); using local storage at {local_path}")
        return QdrantClient(path=local_path)
