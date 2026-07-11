"""
Fixed-input tests confirming trend-slope and drift-rate math against
hand-calculated expected values, plus integration tests for the Redis
Streams consumer (dead-lettering, ack, malformed-event handling) using
fakeredis so no real Redis instance is needed to run the suite.

Run with: python -m pytest backend/app/tests/test_enrichment.py -v
"""

import json

import pytest

from ..utils.time_alignment import align_events, bucket_start, GridBucket
from ..workers.features import RollingFeatureStore, _linear_slope, compute_window_stats
from ..ml.anomaly.isolation_forest import ZoneSensorAnomalyDetector
from ..workers.tasks.enrichment_task import EnrichmentWorker, DEAD_LETTER_STREAM_KEY, STREAM_KEY


# ---------------------------------------------------------------------------
# time_alignment.py
# ---------------------------------------------------------------------------

def test_bucket_start_rounds_down_to_grid():
    assert bucket_start(125, grid_s=60) == 120
    assert bucket_start(59, grid_s=60) == 0
    assert bucket_start(3660, grid_s=60) == 3660


def test_align_events_buckets_and_reduces_mean():
    events = [
        {"event_type": "sensor_reading", "zone_id": "z1", "sensor_type": "gas_ppm",
         "sim_time_s": 10, "value": 8.0},
        {"event_type": "sensor_reading", "zone_id": "z1", "sensor_type": "gas_ppm",
         "sim_time_s": 20, "value": 12.0},
        {"event_type": "sensor_reading", "zone_id": "z1", "sensor_type": "gas_ppm",
         "sim_time_s": 65, "value": 100.0},  # falls in next 60s bucket
    ]
    aligned = align_events(events, grid_s=60, reducer="mean")
    bkt0 = GridBucket("z1", 0.0, 60)
    bkt1 = GridBucket("z1", 60.0, 60)
    assert aligned[bkt0]["gas_ppm"] == pytest.approx(10.0)  # mean(8, 12)
    assert aligned[bkt1]["gas_ppm"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# features.py -- hand-calculated trend-slope / drift-rate math
# ---------------------------------------------------------------------------

def test_linear_slope_perfect_line():
    # value = 2*t + 3 exactly -> slope must be exactly 2.0 (value-unit/s)
    times = [0, 10, 20, 30, 40]
    values = [3, 23, 43, 63, 83]
    assert _linear_slope(times, values) == pytest.approx(2.0)


def test_linear_slope_flat_line_is_zero():
    times = [0, 60, 120, 180]
    values = [8.0, 8.0, 8.0, 8.0]
    assert _linear_slope(times, values) == pytest.approx(0.0)


def test_linear_slope_single_point_is_zero():
    assert _linear_slope([5], [10]) == 0.0
    assert _linear_slope([], []) == 0.0


def test_compute_window_stats_matches_hand_calculation():
    # 3 points: (0, 10), (60, 16), (120, 22) -> slope = (22-10)/(120-0) = 0.1/s
    times = [0, 60, 120]
    values = [10, 16, 22]
    stats = compute_window_stats(times, values)
    assert stats["mean"] == pytest.approx((10 + 16 + 22) / 3)
    assert stats["max"] == 22
    assert stats["trend_slope_per_s"] == pytest.approx(0.1)
    assert stats["drift_rate_per_min"] == pytest.approx(0.1 * 60)  # 6.0/min
    assert stats["n"] == 3


def test_compute_window_stats_empty_window():
    stats = compute_window_stats([], [])
    assert stats == {"mean": None, "max": None, "trend_slope_per_s": 0.0,
                      "drift_rate_per_min": 0.0, "n": 0}


def test_rolling_feature_store_matches_compound_risk_scenario_slope():
    """
    Mirrors the compound_risk_scenario_1.py drift: gas_ppm rises at exactly
    0.01 ppm/s starting from a known baseline. After feeding 10 minutes of
    1Hz readings, the 5-min window's trend_slope_per_s must recover ~0.01
    (hand-calculated ground truth from the scenario's own drift function).
    """
    store = RollingFeatureStore()
    baseline = 8.0
    slope = 0.01
    for t in range(0, 601):  # 0..600s inclusive, 1Hz
        value = baseline + slope * t
        store.ingest("zone-01-degassing", "gas_ppm", t, value)

    feats = store.features("zone-01-degassing", "gas_ppm", sim_time_s=600)
    assert feats["5min"]["trend_slope_per_s"] == pytest.approx(slope, abs=1e-6)
    assert feats["5min"]["drift_rate_per_min"] == pytest.approx(slope * 60, abs=1e-4)
    assert feats["5min"]["n"] == 301  # t=300..600 inclusive at 1Hz


def test_rolling_feature_store_trims_old_data():
    store = RollingFeatureStore(windows={"5min": 300})
    for t in range(0, 4000, 100):
        store.ingest("z1", "temp_c", t, 20.0)
    # internal buffer should never exceed the largest configured window
    buf = store._buffers[("z1", "temp_c")]
    assert buf.times[-1] - buf.times[0] <= 300


# ---------------------------------------------------------------------------
# isolation_forest.py
# ---------------------------------------------------------------------------

def test_anomaly_detector_returns_zero_before_enough_data():
    det = ZoneSensorAnomalyDetector(min_samples=60)
    for i in range(10):
        score = det.score("z1", "gas_ppm", 8.0, {"5min": {"mean": 8.0, "trend_slope_per_s": 0.0},
                                                    "15min": {"trend_slope_per_s": 0.0}})
    assert score == 0.0  # cold start: no model fit yet


def test_anomaly_detector_flags_outlier_after_fitting():
    det = ZoneSensorAnomalyDetector(min_samples=60, refit_every=60, seed=1)
    normal_feats = {"5min": {"mean": 8.0, "trend_slope_per_s": 0.0}, "15min": {"trend_slope_per_s": 0.0}}
    for _ in range(80):
        det.score("z1", "gas_ppm", 8.0 + (_ % 3) * 0.05, normal_feats)  # tight normal cluster

    outlier_feats = {"5min": {"mean": 40.0, "trend_slope_per_s": 0.5}, "15min": {"trend_slope_per_s": 0.5}}
    normal_score = det.score("z1", "gas_ppm", 8.02, normal_feats)
    outlier_score = det.score("z1", "gas_ppm", 40.0, outlier_feats)
    assert outlier_score > normal_score


# ---------------------------------------------------------------------------
# enrichment_task.py -- Redis Streams consumer, via fakeredis
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_redis():
    fakeredis = pytest.importorskip("fakeredis")
    return fakeredis.FakeStrictRedis(decode_responses=False)


class FakeGraphClient:
    def __init__(self):
        self.updates = []
        self.events = []

    def update_zone_properties(self, zone_id, properties):
        self.updates.append((zone_id, properties))

    def record_event(self, event):
        self.events.append(event)


def _xadd_event(redis_client, event: dict):
    redis_client.xadd(STREAM_KEY, {"payload": json.dumps(event)})


def test_enrichment_worker_processes_sensor_reading(fake_redis):
    graph = FakeGraphClient()
    worker = EnrichmentWorker(fake_redis, graph_client=graph, consumer_name="test-worker")

    _xadd_event(fake_redis, {"event_type": "sensor_reading", "zone_id": "z1",
                              "sensor_type": "gas_ppm", "value": 9.0, "sim_time_s": 10})
    n = worker.poll_once(block_ms=100)

    assert n == 1
    assert worker.metrics.processed == 1
    assert len(graph.updates) == 1
    zone_id, props = graph.updates[0]
    assert zone_id == "z1"
    assert props["gas_ppm_last_value"] == 9.0


def test_enrichment_worker_dead_letters_malformed_event(fake_redis):
    worker = EnrichmentWorker(fake_redis, graph_client=FakeGraphClient(), consumer_name="test-worker")

    # missing event_type entirely -> should be dead-lettered, not crash the worker
    fake_redis.xadd(STREAM_KEY, {"payload": json.dumps({"zone_id": "z1"})})
    n = worker.poll_once(block_ms=100)

    assert n == 1
    assert worker.metrics.dead_lettered == 1
    dlq_entries = fake_redis.xrange(DEAD_LETTER_STREAM_KEY)
    assert len(dlq_entries) == 1


def test_enrichment_worker_passes_through_non_sensor_events(fake_redis):
    graph = FakeGraphClient()
    worker = EnrichmentWorker(fake_redis, graph_client=graph, consumer_name="test-worker")

    _xadd_event(fake_redis, {"event_type": "permit_issued", "zone_id": "z1",
                              "permit_id": "PMT-1", "sim_time_s": 5})
    worker.poll_once(block_ms=100)

    assert len(graph.events) == 1
    assert graph.events[0]["permit_id"] == "PMT-1"
