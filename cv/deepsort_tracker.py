"""
DeepSORT tracking.

Assigns persistent worker IDs across frames to compute zone dwell-time and
avoid duplicate-counting the same worker as multiple violations (a single
worker without a hard-hat should generate ONE violation event, not one per
frame they're visible).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from deep_sort_realtime.deepsort_tracker import DeepSort

from .yolo_detector import Detection


@dataclass
class TrackedWorker:
    track_id: str
    box_xyxy: tuple
    confidence: float
    zone_id: str
    first_seen_sim_time_s: float
    last_seen_sim_time_s: float

    @property
    def dwell_time_s(self) -> float:
        return self.last_seen_sim_time_s - self.first_seen_sim_time_s


class DeepSortZoneTracker:
    """
    One tracker instance per zone (DeepSORT's internal state -- Kalman
    filters, appearance embeddings -- is per-camera-feed, so zones must not
    share a tracker or IDs would collide across independent feeds).
    """

    def __init__(self, zone_id: str, max_age: int = 15, n_init: int = 2):
        self.zone_id = zone_id
        self._tracker = DeepSort(max_age=max_age, n_init=n_init)
        self._first_seen: Dict[str, float] = {}
        self.id_switch_count = 0
        self._prev_track_ids = set()

    def update(self, detections: List[Detection], frame_bgr, sim_time_s: float) -> List[TrackedWorker]:
        person_dets = [d for d in detections if d.class_name == "person"]
        # deep-sort-realtime expects ([x, y, w, h], confidence, class_name)
        raw = []
        for d in person_dets:
            x1, y1, x2, y2 = d.box_xyxy
            raw.append(([x1, y1, x2 - x1, y2 - y1], d.confidence, d.class_name))

        tracks = self._tracker.update_tracks(raw, frame=frame_bgr)

        current_ids = set()
        workers = []
        for t in tracks:
            if not t.is_confirmed():
                continue
            track_id = str(t.track_id)
            current_ids.add(track_id)
            if track_id not in self._first_seen:
                self._first_seen[track_id] = sim_time_s
            l, t_, r, b = t.to_ltrb()
            workers.append(TrackedWorker(
                track_id=track_id, box_xyxy=(l, t_, r, b),
                confidence=getattr(t, "det_conf", None) or 0.0,
                zone_id=self.zone_id,
                first_seen_sim_time_s=self._first_seen[track_id],
                last_seen_sim_time_s=sim_time_s,
            ))

        # A crude ID-switch proxy for the validation metrics in Module 4's
        # checklist: count IDs that vanish and are immediately replaced by a
        # *new* ID in the very next update while roughly the same number of
        # people are on screen (a real ID-switch benchmark needs ground-truth
        # trajectories; this is a same-frame-count heuristic for the demo).
        vanished = self._prev_track_ids - current_ids
        appeared = current_ids - self._prev_track_ids
        if vanished and appeared and len(current_ids) == len(self._prev_track_ids):
            self.id_switch_count += min(len(vanished), len(appeared))
        self._prev_track_ids = current_ids

        return workers
