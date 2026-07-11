"""
Frame ingestor.

Reads pre-recorded/looped per-zone clips (stand-in for live RTSP) at
~2-5 fps, feeds frames into the detection loop. Also supports a synthetic
frame generator for local dev/tests when no real clips are on disk yet --
draws simple person-shaped rectangles with/without a hard-hat marker so the
rest of the pipeline (detector -> tracker -> PPE classifier -> occupancy)
can be exercised end-to-end without any video assets.
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class Frame:
    zone_id: str
    frame_bgr: np.ndarray
    frame_index: int
    sim_time_s: float


class VideoClipIngestor:
    """Loops a real video file for one zone at a target sample rate."""

    def __init__(self, zone_id: str, clip_path: str, sample_fps: float = 3.0):
        self.zone_id = zone_id
        self.clip_path = str(clip_path)
        self.sample_fps = sample_fps
        self._cap = cv2.VideoCapture(self.clip_path)
        if not self._cap.isOpened():
            raise FileNotFoundError(f"Could not open clip: {self.clip_path}")
        self._source_fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._frame_stride = max(1, round(self._source_fps / self.sample_fps))
        self._frame_index = 0

    def frames(self) -> Iterator[Frame]:
        idx = 0
        while True:
            ok, frame = self._cap.read()
            if not ok:
                # loop back to start (stand-in for a live feed that never ends)
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self._cap.read()
                if not ok:
                    break
            if idx % self._frame_stride == 0:
                yield Frame(zone_id=self.zone_id, frame_bgr=frame,
                            frame_index=self._frame_index, sim_time_s=self._frame_index / self.sample_fps)
                self._frame_index += 1
            idx += 1

    def release(self):
        self._cap.release()


class SyntheticZoneIngestor:
    """
    Generates synthetic frames with 0-N moving "worker" rectangles, each
    either wearing a hard-hat (green marker) or not (red marker), so the
    full pipeline can be validated without real footage. Deterministic
    given a seed, for repeatable tests.
    """

    def __init__(self, zone_id: str, num_frames: int = 60, width: int = 640, height: int = 480,
                 sample_fps: float = 3.0, seed: int = 0,
                 worker_specs: Optional[List[dict]] = None):
        """
        worker_specs: optional list of {"start_x", "start_y", "dx", "dy",
        "has_ppe"} to script specific worker trajectories/compliance for
        tests. If None, generates `num_frames`-appropriate random workers.
        """
        self.zone_id = zone_id
        self.num_frames = num_frames
        self.width = width
        self.height = height
        self.sample_fps = sample_fps
        self.rng = np.random.default_rng(seed)

        self.workers = worker_specs or self._random_workers()

    def _random_workers(self) -> List[dict]:
        n = int(self.rng.integers(1, 4))
        specs = []
        for _ in range(n):
            specs.append({
                "start_x": int(self.rng.integers(50, self.width - 100)),
                "start_y": int(self.rng.integers(50, self.height - 100)),
                "dx": float(self.rng.uniform(-3, 3)),
                "dy": float(self.rng.uniform(-2, 2)),
                "has_ppe": bool(self.rng.random() > 0.3),
            })
        return specs

    def frames(self) -> Iterator[Frame]:
        for i in range(self.num_frames):
            img = np.full((self.height, self.width, 3), 40, dtype=np.uint8)  # dim gray background
            for w in self.workers:
                x = int(w["start_x"] + w["dx"] * i) % (self.width - 60)
                y = int(w["start_y"] + w["dy"] * i) % (self.height - 100)
                # body
                cv2.rectangle(img, (x, y + 20), (x + 40, y + 100), (150, 150, 150), -1)
                # head + PPE marker (green = hard hat, red = none)
                color = (0, 200, 0) if w["has_ppe"] else (0, 0, 200)
                cv2.circle(img, (x + 20, y + 10), 15, color, -1)
            yield Frame(zone_id=self.zone_id, frame_bgr=img, frame_index=i,
                        sim_time_s=i / self.sample_fps)


def frames_from_clip_dir(clip_dir: str, sample_fps: float = 3.0) -> List[VideoClipIngestor]:
    """
    Convenience: one VideoClipIngestor per file named `<zone_id>.mp4` (or
    .avi/.mov) in `clip_dir`, for wiring up multiple zones at once.
    """
    ingestors = []
    for path in sorted(Path(clip_dir).glob("*")):
        if path.suffix.lower() not in (".mp4", ".avi", ".mov", ".mkv"):
            continue
        zone_id = path.stem
        ingestors.append(VideoClipIngestor(zone_id, str(path), sample_fps=sample_fps))
    return ingestors


SNAPSHOT_DIR = Path(__file__).resolve().parent / "_violation_snapshots"


def build_detection_event(zone_id: str, sim_time_s: float, worker_count: int,
                           ppe_violation: bool, confidence: float) -> dict:
    """
    Detection event shape posted to the enrichment queue:
    (worker_count, ppe_violation, zone_id, timestamp, confidence).
    """
    return {
        "event_type": "cv_detection",
        "zone_id": zone_id,
        "sim_time_s": sim_time_s,
        "worker_count": worker_count,
        "ppe_violation": ppe_violation,
        "confidence": confidence,
    }


def save_violation_snapshot(frame: Frame, track_id: str, snapshot_dir: Optional[Path] = None) -> str:
    """
    Saves the annotated frame to (local-disk stand-in for) object storage,
    ONLY called on an actual violation event -- storage cost stays bounded
    since we don't snapshot every frame, just the ones worth reviewing.
    Returns the path the frame was saved to.
    """
    out_dir = snapshot_dir or SNAPSHOT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{frame.zone_id}_t{int(frame.sim_time_s)}_track{track_id}.jpg"
    path = out_dir / filename
    cv2.imwrite(str(path), frame.frame_bgr)
    return str(path)
