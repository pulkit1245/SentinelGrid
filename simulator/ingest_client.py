"""
Thin HTTP client for posting simulated events to the backend ingest endpoint.

Falls back to local console/JSONL logging if the backend isn't reachable yet,
so this module is independently runnable/demoable before the backend exists.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

DEFAULT_BASE_URL = os.environ.get("SENTINELGRID_API_BASE", "http://localhost:8000")
SENSOR_INGEST_PATH = "/api/v1/sensors/ingest"
EVENT_INGEST_PATH = "/api/v1/events/ingest"  # generic (permit / shift / cv)

LOG_DIR = Path(__file__).resolve().parent / "_local_event_log"
LOG_DIR.mkdir(exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IngestClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, offline: bool = False,
                 timeout: float = 2.0, retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.offline = offline or requests is None
        self.timeout = timeout
        self.retries = retries
        self._offline_files = {}

    def _offline_log(self, path: str, payload: dict):
        fname = LOG_DIR / (path.strip("/").replace("/", "_") + ".jsonl")
        with open(fname, "a") as f:
            f.write(json.dumps(payload) + "\n")

    def post(self, path: str, payload: dict) -> bool:
        payload = {**payload, "_emitted_at": _now_iso()}
        if self.offline:
            self._offline_log(path, payload)
            return True

        url = f"{self.base_url}{path}"
        for attempt in range(self.retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=self.timeout)
                if resp.status_code < 300:
                    return True
                print(f"[ingest] {path} -> HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as exc:  # noqa: BLE001
                if attempt == self.retries:
                    print(f"[ingest] failed to reach {url} ({exc}); falling back to offline log")
                    self._offline_log(path, payload)
                    return False
                time.sleep(0.2 * (attempt + 1))
        return False

    def post_sensor(self, payload: dict) -> bool:
        return self.post(SENSOR_INGEST_PATH, payload)

    def post_event(self, payload: dict) -> bool:
        return self.post(EVENT_INGEST_PATH, payload)
