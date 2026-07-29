"""
Persistent Object & Face Tracking Engine.
Uses Intersection over Union (IoU) matching, Exponential Moving Average (EMA) coordinate smoothing,
and temporal persistence filtering to eliminate flicker and assign unique tracking IDs.
"""

import time
import numpy as np
from typing import List, Dict, Any, Tuple


def compute_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Compute Intersection over Union (IoU) ratio between two bounding boxes (x, y, w, h)."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]

    iou = interArea / float(boxAArea + boxBArea - interArea + 1e-6)
    return iou


class TrackedObject:
    def __init__(self, track_id: int, label: str, box: Tuple[int, int, int, int], confidence: float):
        self.track_id = track_id
        self.label = label
        self.box = np.array(box, dtype=np.float32)  # (x, y, w, h)
        self.confidence = confidence
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.consecutive_frames = 1
        self.stale_frames = 0

    def update(self, new_box: Tuple[int, int, int, int], confidence: float, alpha: float = 0.4):
        """EMA bounding box coordinate smoothing to eliminate flicker."""
        new_box_arr = np.array(new_box, dtype=np.float32)
        self.box = alpha * new_box_arr + (1 - alpha) * self.box
        self.confidence = max(self.confidence, confidence)
        self.last_seen = time.time()
        self.consecutive_frames += 1
        self.stale_frames = 0

    def to_dict(self) -> Dict[str, Any]:
        x, y, w, h = self.box.astype(int)
        return {
            "track_id": self.track_id,
            "label": self.label,
            "box": (int(x), int(y), int(w), int(h)),
            "confidence": float(self.confidence),
            "consecutive_frames": self.consecutive_frames,
            "duration_sec": round(time.time() - self.first_seen, 2)
        }


class IoUTracker:
    def __init__(self, iou_threshold: float = 0.35, max_stale: int = 5):
        self.iou_threshold = iou_threshold
        self.max_stale = max_stale
        self.tracks: List[TrackedObject] = []
        self.next_track_id = 1

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match incoming frame detections to active tracks via IoU.
        Input: list of {"box": (x, y, w, h), "label": str, "confidence": float}
        Returns list of smoothed, tracked detections with track IDs.
        """
        # Mark all existing tracks as candidate stale
        for track in self.tracks:
            track.stale_frames += 1

        matched_det_indices = set()

        for det_idx, det in enumerate(detections):
            det_box = det["box"]
            det_label = det["label"]
            det_conf = det["confidence"]

            best_iou = 0.0
            best_track = None

            for track in self.tracks:
                if track.label == det_label:
                    iou = compute_iou(tuple(track.box.astype(int)), det_box)
                    if iou > best_iou and iou >= self.iou_threshold:
                        best_iou = iou
                        best_track = track

            if best_track is not None:
                best_track.update(det_box, det_conf)
                matched_det_indices.add(det_idx)
            else:
                # Create new persistent track
                new_track = TrackedObject(self.next_track_id, det_label, det_box, det_conf)
                self.next_track_id += 1
                self.tracks.append(new_track)

        # Remove stale tracks that disappeared for max_stale frames
        self.tracks = [t for t in self.tracks if t.stale_frames < self.max_stale]

        return [t.to_dict() for t in self.tracks]
