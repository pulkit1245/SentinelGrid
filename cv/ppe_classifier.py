"""
PPE classifier & zone-occupancy counter.

Per-worker compliance flag: for each tracked worker, checks whether a
"hard_hat"/"vest" detection box overlaps their person box (IoU-based
association) versus a "no_hard_hat" detection, and assigns a compliance
verdict. Per-zone occupancy count is published as a rolling-window feature
into the enrichment queue.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .deepsort_tracker import TrackedWorker
from .yolo_detector import Detection

PPE_POSITIVE_CLASSES = {"hard_hat", "vest"}
PPE_NEGATIVE_CLASSES = {"no_hard_hat"}
IOU_ASSOCIATION_THRESHOLD = 0.6


def _iou(box_a: tuple, box_b: tuple) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_w, inter_h = max(0.0, inter_x2 - inter_x1), max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


def _containment_ratio(box_a: tuple, box_b: tuple) -> float:
    """
    Fraction of the SMALLER box's area that overlaps the other box. Used
    (instead of raw IoU) to associate a small PPE detection (hard-hat,
    typically covering just the head) with a much larger person box --
    IoU alone would almost never clear a sane threshold for boxes with
    that size mismatch, systematically under-associating real detections.
    """
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_w, inter_h = max(0.0, inter_x2 - inter_x1), max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    smaller = min(area_a, area_b)
    return inter_area / smaller if smaller > 0 else 0.0


@dataclass
class ComplianceResult:
    track_id: str
    compliant: bool  # True if wearing required PPE, False if flagged, None-equivalent handled via `status`
    status: str  # "compliant" | "violation" | "unknown"
    matched_ppe_classes: List[str]


class PPEClassifier:
    def __init__(self, iou_threshold: float = IOU_ASSOCIATION_THRESHOLD):
        self.iou_threshold = iou_threshold

    def classify(self, workers: List[TrackedWorker], detections: List[Detection]) -> List[ComplianceResult]:
        ppe_dets = [d for d in detections if d.class_name in PPE_POSITIVE_CLASSES | PPE_NEGATIVE_CLASSES]
        results = []
        for w in workers:
            matched = [d for d in ppe_dets if _containment_ratio(w.box_xyxy, d.box_xyxy) >= self.iou_threshold]
            matched_names = [d.class_name for d in matched]

            if any(n in PPE_NEGATIVE_CLASSES for n in matched_names):
                status = "violation"
                compliant = False
            elif any(n in PPE_POSITIVE_CLASSES for n in matched_names):
                status = "compliant"
                compliant = True
            else:
                # No PPE box overlapped this worker at all -- either the PPE
                # model isn't loaded (base COCO weights only detect "person")
                # or the hard-hat is simply out of frame/occluded. Don't
                # silently treat "unknown" as a violation -- that's exactly
                # the kind of false-positive-driving assumption Module 4's
                # validation step is meant to catch.
                status = "unknown"
                compliant = None

            results.append(ComplianceResult(
                track_id=w.track_id, compliant=compliant, status=status,
                matched_ppe_classes=matched_names,
            ))
        return results


class ZoneOccupancyCounter:
    """
    Tracks rolling per-zone occupancy counts (distinct active track_ids per
    zone, at the current frame), published as an event into the enrichment
    queue so it lands on the Zone node like any other rolling-window feature.
    """

    def __init__(self):
        self._history: Dict[str, List[dict]] = {}  # zone_id -> [{sim_time_s, count}, ...]

    def record(self, zone_id: str, sim_time_s: float, workers: List[TrackedWorker]):
        self._history.setdefault(zone_id, []).append({
            "sim_time_s": sim_time_s, "count": len(workers),
        })

    def current_count(self, zone_id: str) -> int:
        hist = self._history.get(zone_id, [])
        return hist[-1]["count"] if hist else 0

    def rolling_mean(self, zone_id: str, sim_time_s: float, window_s: float = 300.0) -> Optional[float]:
        hist = self._history.get(zone_id, [])
        window = [h["count"] for h in hist if sim_time_s - window_s <= h["sim_time_s"] <= sim_time_s]
        return sum(window) / len(window) if window else None

    def to_event(self, zone_id: str, sim_time_s: float) -> dict:
        return {
            "event_type": "cv_zone_occupancy",
            "zone_id": zone_id,
            "sim_time_s": sim_time_s,
            "occupancy_count": self.current_count(zone_id),
        }
