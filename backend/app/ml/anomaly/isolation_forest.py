"""
Isolation Forest anomaly detector.

Flags sensor drift *before* it crosses the absolute statutory threshold, by
scoring how unusual the current rolling-window feature vector is relative
to the zone/sensor's own recent history. Output (an anomaly score in
[0, 1], higher = more anomalous) feeds into the Compound Risk Agent as an
additional signal alongside the raw trend slope.

Trained per (zone_id, sensor_type) since baselines differ wildly across
zones (compressor vibration baseline is not comparable to control-room
vibration baseline). Falls back to "not anomalous" (score 0.0) until a
model has seen enough data to fit, so a cold worker doesn't immediately
start flagging everything.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from sklearn.ensemble import IsolationForest
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "scikit-learn is required for the anomaly detector: "
        "pip install scikit-learn --break-system-packages"
    ) from exc

MIN_SAMPLES_TO_FIT = 60          # need this many observations before fitting
REFIT_EVERY_N_SAMPLES = 60       # refit periodically as new data arrives
CONTAMINATION = 0.05             # expected fraction of anomalous points


class ZoneSensorAnomalyDetector:
    """
    One Isolation Forest per (zone_id, sensor_type), operating on a small
    feature vector: [value, 5min_mean, 5min_slope, 15min_slope].
    """

    def __init__(self, contamination: float = CONTAMINATION,
                 min_samples: int = MIN_SAMPLES_TO_FIT,
                 refit_every: int = REFIT_EVERY_N_SAMPLES,
                 seed: int = 13):
        self.contamination = contamination
        self.min_samples = min_samples
        self.refit_every = refit_every
        self.seed = seed
        self._history: Dict[Tuple[str, str], List[List[float]]] = defaultdict(list)
        self._models: Dict[Tuple[str, str], IsolationForest] = {}
        self._since_refit: Dict[Tuple[str, str], int] = defaultdict(int)

    def _feature_vector(self, value: float, feats: dict) -> List[float]:
        f5 = feats.get("5min", {})
        f15 = feats.get("15min", {})
        return [
            value,
            f5.get("mean") if f5.get("mean") is not None else value,
            f5.get("trend_slope_per_s", 0.0),
            f15.get("trend_slope_per_s", 0.0),
        ]

    def _maybe_fit(self, key: Tuple[str, str]):
        history = self._history[key]
        if len(history) < self.min_samples:
            return
        due_for_refit = (key not in self._models
                          or self._since_refit[key] >= self.refit_every)
        if not due_for_refit:
            return
        model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=self.seed,
        )
        model.fit(np.array(history))
        self._models[key] = model
        self._since_refit[key] = 0

    def score(self, zone_id: str, sensor_type: str, value: float,
              rolling_features: dict) -> float:
        """
        Returns an anomaly score in [0, 1] (higher = more anomalous).
        Updates internal history/model state as a side effect (call once
        per reading, in time order).
        """
        key = (zone_id, sensor_type)
        vec = self._feature_vector(value, rolling_features)
        self._history[key].append(vec)
        self._since_refit[key] += 1
        # keep history bounded so memory doesn't grow unboundedly over a 48h run
        if len(self._history[key]) > 5000:
            self._history[key] = self._history[key][-5000:]

        self._maybe_fit(key)

        model = self._models.get(key)
        if model is None:
            return 0.0

        # decision_function: higher = more normal. Convert to a 0-1
        # "anomalousness" score via the model's own score_samples range
        # rather than a fixed constant, so it adapts per zone/sensor.
        raw = model.decision_function(np.array([vec]))[0]
        # squash: decision_function is roughly in [-0.5, 0.5]; anomalies are negative.
        score = max(0.0, min(1.0, 0.5 - raw))
        return round(float(score), 4)


class AnomalyDetectorRegistry:
    """Thin convenience wrapper the enrichment worker holds one instance of."""

    def __init__(self, **kwargs):
        self._detector = ZoneSensorAnomalyDetector(**kwargs)

    def score(self, zone_id: str, sensor_type: str, value: float,
              rolling_features: dict) -> float:
        return self._detector.score(zone_id, sensor_type, value, rolling_features)
