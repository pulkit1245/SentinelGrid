"""
CV pipeline orchestrator.

Wires frame_ingestor -> yolo_detector -> deepsort_tracker -> ppe_classifier
-> zone_occupancy_counter -> event publishing into a single per-zone loop,
mirroring the simulator's plant_simulator.py role for Module 4.
"""

import sys
from pathlib import Path
from typing import Iterable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from simulator.ingest_client import IngestClient  # noqa: E402

from .deepsort_tracker import DeepSortZoneTracker
from .frame_ingestor import Frame, build_detection_event, save_violation_snapshot
from .ppe_classifier import PPEClassifier, ZoneOccupancyCounter
from .yolo_detector import YoloDetector


class ZoneCVPipeline:
    def __init__(self, zone_id: str, detector: Optional[YoloDetector] = None,
                 ingest_client: Optional[IngestClient] = None, save_snapshots: bool = True):
        self.zone_id = zone_id
        self.detector = detector or YoloDetector()
        self.tracker = DeepSortZoneTracker(zone_id)
        self.classifier = PPEClassifier()
        self.occupancy = ZoneOccupancyCounter()
        self.client = ingest_client or IngestClient(offline=True)
        self.save_snapshots = save_snapshots

        self._already_violating: set = set()  # track_ids currently flagged, to snapshot once per episode

    def process_frame(self, frame: Frame) -> dict:
        detections = self.detector.detect(frame.frame_bgr)
        workers = self.tracker.update(detections, frame.frame_bgr, frame.sim_time_s)
        compliance = self.classifier.classify(workers, detections)
        self.occupancy.record(self.zone_id, frame.sim_time_s, workers)

        violating_ids = {c.track_id for c in compliance if c.status == "violation"}
        newly_violating = violating_ids - self._already_violating
        self._already_violating = violating_ids

        for track_id in newly_violating:
            if self.save_snapshots:
                save_violation_snapshot(frame, track_id)

        confidences = [d.confidence for d in detections if d.class_name == "person"]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        event = build_detection_event(
            zone_id=self.zone_id, sim_time_s=frame.sim_time_s,
            worker_count=len(workers), ppe_violation=len(violating_ids) > 0,
            confidence=avg_conf,
        )
        self.client.post_event(event)
        self.client.post_event(self.occupancy.to_event(self.zone_id, frame.sim_time_s))

        return {
            "detections": detections, "workers": workers,
            "compliance": compliance, "newly_violating": newly_violating,
        }

    def run(self, frames: Iterable[Frame]):
        for frame in frames:
            yield self.process_frame(frame)
