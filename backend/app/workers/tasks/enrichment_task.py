"""
Enrichment worker.

Consumes raw sensor/permit/CV events off a Redis Streams ingest queue,
computes rolling-window features (via RollingFeatureStore) and an
Isolation-Forest anomaly score, and writes the resulting feature set back
onto the Zone node in the Plant Risk Graph (via a pluggable graph_client --
Neo4j in production, networkx fallback for local dev, matching Module 3's
shared_blackboard client).

Consumer-group semantics (XREADGROUP) so multiple worker replicas could run
in parallel without double-processing, with explicit ACK on success and a
dead-letter stream for malformed events so a single bad payload can't wedge
the whole queue.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

from ..features import RollingFeatureStore
from ...ml.anomaly.isolation_forest import AnomalyDetectorRegistry
from ...utils.time_alignment import bucket_start
from ...core.ingest_queue import (
    DEAD_LETTER_LIST_KEY,
    DEAD_LETTER_STREAM_KEY,
    INGEST_LIST_KEY,
    streams_supported,
)

logger = logging.getLogger("sentinelgrid.enrichment")

STREAM_KEY = "sentinelgrid:ingest"
DEAD_LETTER_STREAM_KEY = "sentinelgrid:ingest:dead_letter"
CONSUMER_GROUP = "enrichment_workers"

MAX_RETRIES = 3
RETRY_BACKOFF_BASE_S = 0.5


@dataclass
class EnrichmentMetrics:
    processed: int = 0
    dead_lettered: int = 0
    retried: int = 0
    queue_depth: int = 0  # updated each poll; exported for the demo cockpit


class EnrichmentWorker:
    def __init__(self, redis_client, graph_client=None,
                 consumer_name: str = "worker-1",
                 stream_key: str = STREAM_KEY,
                 group: str = CONSUMER_GROUP,
                 feature_store: Optional[RollingFeatureStore] = None,
                 anomaly_registry: Optional[AnomalyDetectorRegistry] = None,
                 on_feature_update: Optional[Callable[[str, dict], None]] = None):
        """
        graph_client needs a `.update_zone_properties(zone_id, properties: dict)`
        method -- satisfied by both agents/graph_client.py (Neo4j) and its
        networkx fallback from Module 3.

        on_feature_update is an optional hook (mainly for tests) called with
        (zone_id, features_dict) every time a sensor_reading is processed,
        instead of/in addition to writing to the graph client.
        """
        self.redis = redis_client
        self.graph_client = graph_client
        self.consumer_name = consumer_name
        self.stream_key = stream_key
        self.group = group
        self.feature_store = feature_store or RollingFeatureStore()
        self.anomaly_registry = anomaly_registry or AnomalyDetectorRegistry()
        self.on_feature_update = on_feature_update
        self.metrics = EnrichmentMetrics()
        self._use_list = not streams_supported(self.redis)

        if self._use_list:
            logger.info("Redis streams unavailable — using list queue (%s)", INGEST_LIST_KEY)
        else:
            self._ensure_group()

    def _ensure_group(self):
        try:
            self.redis.xgroup_create(self.stream_key, self.group, id="0", mkstream=True)
        except Exception as exc:  # noqa: BLE001
            # BUSYGROUP = group already exists, which is fine on worker restart
            if "BUSYGROUP" not in str(exc):
                raise

    def _decode_raw_fields(self, raw_fields: dict) -> dict:
        decoded = {}
        for k, v in raw_fields.items():
            key = k.decode("utf-8") if isinstance(k, bytes) else k
            val = v.decode("utf-8") if isinstance(v, bytes) else v
            decoded[key] = val
        return decoded

    def _dead_letter(self, entry_id, raw_fields: dict, reason: str):
        entry_id_str = entry_id.decode("utf-8") if isinstance(entry_id, bytes) else str(entry_id)
        payload = {**self._decode_raw_fields(raw_fields), "_dlq_reason": reason,
                   "_dlq_original_id": entry_id_str}
        encoded = json.dumps(payload)
        if self._use_list:
            self.redis.lpush(DEAD_LETTER_LIST_KEY, encoded)
        else:
            self.redis.xadd(DEAD_LETTER_STREAM_KEY, {"payload": encoded})
        self.metrics.dead_lettered += 1
        logger.warning("Dead-lettered event %s: %s", entry_id_str, reason)

    def _dead_letter_payload(self, payload: str, reason: str):
        self.redis.lpush(DEAD_LETTER_LIST_KEY, json.dumps({"payload": payload, "_dlq_reason": reason}))
        self.metrics.dead_lettered += 1
        logger.warning("Dead-lettered list event: %s", reason)

    def _parse_event(self, raw_fields: dict) -> dict:
        payload_str = raw_fields.get("payload") or raw_fields.get(b"payload")
        if isinstance(payload_str, bytes):
            payload_str = payload_str.decode("utf-8")
        if payload_str is None:
            raise ValueError("missing 'payload' field")
        event = json.loads(payload_str)
        if "event_type" not in event:
            raise ValueError("missing 'event_type'")
        return event

    def _process_sensor_reading(self, event: dict):
        zone_id = event["zone_id"]
        sensor_type = event["sensor_type"]
        value = event["value"]
        sim_time_s = event["sim_time_s"]

        self.feature_store.ingest(zone_id, sensor_type, sim_time_s, value)
        rolling = self.feature_store.features(zone_id, sensor_type, sim_time_s)
        anomaly_score = self.anomaly_registry.score(zone_id, sensor_type, value, rolling)

        feature_update = {
            f"{sensor_type}_5min_mean": rolling["5min"]["mean"],
            f"{sensor_type}_5min_slope_per_s": rolling["5min"]["trend_slope_per_s"],
            f"{sensor_type}_15min_slope_per_s": rolling["15min"]["trend_slope_per_s"],
            f"{sensor_type}_60min_slope_per_s": rolling["60min"]["trend_slope_per_s"],
            f"{sensor_type}_drift_rate_per_min": rolling["5min"]["drift_rate_per_min"],
            f"{sensor_type}_anomaly_score": anomaly_score,
            f"{sensor_type}_last_value": value,
            f"{sensor_type}_last_updated_bucket": bucket_start(sim_time_s),
        }

        if self.graph_client is not None:
            self.graph_client.update_zone_properties(zone_id, feature_update)
        if self.on_feature_update is not None:
            self.on_feature_update(zone_id, feature_update)

    def _process_event(self, event: dict):
        et = event["event_type"]
        if et == "sensor_reading":
            self._process_sensor_reading(event)
        else:
            # Non-sensor events (permit/shift/cv) get written straight through
            # to the graph client as-is; Module 3's agents read them off the
            # Zone/Permit nodes directly. Enrichment's job here is just to
            # make sure they land, not to feature-engineer them further.
            if self.graph_client is not None and hasattr(self.graph_client, "record_event"):
                self.graph_client.record_event(event)

    def _handle_entry(self, entry_id: str, raw_fields: dict):
        for attempt in range(MAX_RETRIES + 1):
            try:
                event = self._parse_event(raw_fields)
            except (ValueError, json.JSONDecodeError) as exc:
                # Malformed payload -- no amount of retrying fixes this.
                self._dead_letter(entry_id, raw_fields, f"parse_error: {exc}")
                self.redis.xack(self.stream_key, self.group, entry_id)
                return

            try:
                self._process_event(event)
                self.redis.xack(self.stream_key, self.group, entry_id)
                self.metrics.processed += 1
                return
            except Exception as exc:  # noqa: BLE001  -- transient (e.g. DB) errors
                if attempt == MAX_RETRIES:
                    self._dead_letter(entry_id, raw_fields, f"max_retries_exceeded: {exc}")
                    self.redis.xack(self.stream_key, self.group, entry_id)
                    return
                self.metrics.retried += 1
                backoff = RETRY_BACKOFF_BASE_S * (2 ** attempt)
                logger.warning("Retrying entry %s after error: %s (backoff=%.2fs)",
                                entry_id, exc, backoff)
                time.sleep(backoff)

    def _process_list_payload(self, payload: str) -> bool:
        for attempt in range(MAX_RETRIES + 1):
            try:
                event = json.loads(payload)
                if "event_type" not in event:
                    raise ValueError("missing 'event_type'")
            except (ValueError, json.JSONDecodeError) as exc:
                self._dead_letter_payload(payload, f"parse_error: {exc}")
                return True

            try:
                self._process_event(event)
                self.metrics.processed += 1
                return True
            except Exception as exc:  # noqa: BLE001
                if attempt == MAX_RETRIES:
                    self._dead_letter_payload(payload, f"max_retries_exceeded: {exc}")
                    return True
                self.metrics.retried += 1
                backoff = RETRY_BACKOFF_BASE_S * (2 ** attempt)
                logger.warning("Retrying list event after error: %s (backoff=%.2fs)", exc, backoff)
                time.sleep(backoff)
        return False

    def poll_once(self, count: int = 50, block_ms: int = 2000) -> int:
        """Reads up to `count` new entries, processes them, returns how many were read."""
        if self._use_list:
            n = 0
            for _ in range(count):
                payload = self.redis.rpop(INGEST_LIST_KEY)
                if not payload:
                    break
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8")
                if self._process_list_payload(payload):
                    n += 1
            if n == 0:
                time.sleep(block_ms / 1000)
            self._update_queue_depth()
            return n

        resp = self.redis.xreadgroup(
            self.group, self.consumer_name,
            {self.stream_key: ">"}, count=count, block=block_ms,
        )
        if not resp:
            self._update_queue_depth()
            return 0

        n = 0
        for _stream_key, entries in resp:
            for entry_id, raw_fields in entries:
                self._handle_entry(entry_id, raw_fields)
                n += 1
        self._update_queue_depth()
        return n

    def _update_queue_depth(self):
        try:
            if self._use_list:
                self.metrics.queue_depth = self.redis.llen(INGEST_LIST_KEY)
            else:
                pending = self.redis.xpending(self.stream_key, self.group)
                self.metrics.queue_depth = pending["pending"] if pending else 0
        except Exception:  # noqa: BLE001
            pass  # metrics are best-effort; never crash the worker over this

    def run_forever(self):
        logger.info("Enrichment worker '%s' starting on stream '%s'",
                     self.consumer_name, self.stream_key)
        while True:
            n = self.poll_once()
            if self.metrics.queue_depth > 500:
                logger.warning("Queue depth %d -- worker may be falling behind",
                                self.metrics.queue_depth)
            if n == 0:
                time.sleep(0.1)


def run_from_cli():  # pragma: no cover
    import argparse
    from app.core.redis_client import get_sync_redis

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-url", default="redis://localhost:6379/0")
    parser.add_argument("--consumer-name", default="worker-1")
    args = parser.parse_args()

    client = get_sync_redis(decode_responses=False)
    worker = EnrichmentWorker(client, consumer_name=args.consumer_name)
    worker.run_forever()


if __name__ == "__main__":  # pragma: no cover
    run_from_cli()
