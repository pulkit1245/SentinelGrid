"""
YOLOv8n detector wrapper.

Loads pretrained weights and runs detection for person + PPE classes
(hard-hat, vest, no-hard-hat). Includes OpenCV preprocessing (resize,
letterbox, brightness correction) ahead of inference.

`models/yolov8n_ppe.pt` currently holds the *base* COCO-pretrained
yolov8n weights (person class only, class id 0) as a placeholder --
swap in the fine-tuned PPE-labeled weights once that training run is
done; the wrapper's public interface (`detect(frame) -> List[Detection]`)
does not change either way. When only the base model is loaded, PPE
class detections are simply absent and `ppe_classifier.py` degrades
gracefully (flags everyone as "unknown" rather than crashing).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

import cv2
import numpy as np
from ultralytics import YOLO

DEFAULT_WEIGHTS = Path(__file__).resolve().parent / "models" / "yolov8n_ppe.pt"

# Class-name mapping for the fine-tuned PPE model. The base COCO model only
# has "person" (id 0); once fine-tuned weights are trained, update this map
# to match the new model's class indices.
PPE_CLASS_NAMES = {
    0: "person",
    1: "hard_hat",
    2: "vest",
    3: "no_hard_hat",
}


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    box_xyxy: tuple  # (x1, y1, x2, y2) in original-frame pixel coords


class YoloDetector:
    def __init__(self, weights_path: str = None, conf_threshold: float = 0.4,
                 imgsz: int = 640, device: str = "cpu"):
        self.weights_path = str(weights_path or DEFAULT_WEIGHTS)
        self.conf_threshold = conf_threshold
        self.imgsz = imgsz
        self.device = device
        self.model = YOLO(self.weights_path)
        # Reflects whatever class map the loaded weights actually use --
        # falls back to PPE_CLASS_NAMES only where the model doesn't supply names.
        self.class_names = {**PPE_CLASS_NAMES, **(self.model.names or {})}

    def preprocess(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Resize/letterbox + brightness correction ahead of inference."""
        h, w = frame_bgr.shape[:2]
        scale = self.imgsz / max(h, w)
        resized = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)))
        # letterbox pad to square imgsz x imgsz
        pad_h = self.imgsz - resized.shape[0]
        pad_w = self.imgsz - resized.shape[1]
        letterboxed = cv2.copyMakeBorder(
            resized, 0, pad_h, 0, pad_w, cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )
        # simple auto brightness correction (CLAHE on the L channel)
        lab = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        corrected = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
        return corrected

    def detect(self, frame_bgr: np.ndarray) -> List[Detection]:
        """
        Runs inference on the raw frame directly (ultralytics does its own
        internal letterboxing/normalization); `preprocess()` above is
        exposed separately for cases where you want the corrected frame
        itself (e.g. for the annotated-snapshot-on-violation feature).
        """
        results = self.model.predict(
            frame_bgr, conf=self.conf_threshold, imgsz=self.imgsz,
            device=self.device, verbose=False,
        )
        detections = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                class_id = int(box.cls.item())
                confidence = float(box.conf.item())
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                detections.append(Detection(
                    class_id=class_id,
                    class_name=self.class_names.get(class_id, f"class_{class_id}"),
                    confidence=confidence,
                    box_xyxy=(x1, y1, x2, y2),
                ))
        return detections

    def detect_persons(self, frame_bgr: np.ndarray) -> List[Detection]:
        return [d for d in self.detect(frame_bgr) if d.class_name == "person"]
