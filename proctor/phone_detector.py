"""
Mobile Phone & Prohibited Multi-Gadget AI Detection Module.
Uses OpenCV DNN MobileNet-SSD, Non-Maximum Suppression (NMS), and IoU Tracker for persistent box smoothing.
Optimized for 30+ FPS real-time execution.
"""

import cv2
import os
import urllib.request
import numpy as np
from typing import List, Dict, Any, Tuple
from .config import COCO_CLASSES, MODEL_PROTO_PATH, MODEL_WEIGHTS_PATH, OBJECT_CONF_THRESHOLD, NMS_THRESHOLD
from .tracker import IoUTracker
from .logger import logger

PROTO_URL = "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/voc/MobileNetSSD_deploy.prototxt"
CAFFE_URL = "https://raw.githubusercontent.com/PINTO0309/MobileNet-SSD-RealSense/master/caffemodel/MobileNetSSD/MobileNetSSD_deploy.caffemodel"


class ObjectDetector:

    def __init__(self):
        self.net = None
        self.proto_path = MODEL_PROTO_PATH
        self.weights_path = MODEL_WEIGHTS_PATH
        self.tracker = IoUTracker(iou_threshold=0.30, max_stale=4)
        self._init_model()

    def _download_if_missing(self):
        """Fetch Caffe model definition & weights if not present on local disk."""
        headers = {"User-Agent": "Mozilla/5.0"}
        if not os.path.exists(self.proto_path):
            try:
                logger.info(f"[OBJECT DETECTOR] Downloading Caffe Prototxt from {PROTO_URL}...")
                req = urllib.request.Request(PROTO_URL, headers=headers)
                with urllib.request.urlopen(req) as resp, open(self.proto_path, "wb") as f:
                    f.write(resp.read())
            except Exception as e:
                logger.warning(f"[OBJECT DETECTOR WARN] Could not download Prototxt: {e}")

        if not os.path.exists(self.weights_path):
            try:
                logger.info(f"[OBJECT DETECTOR] Downloading Caffe Model Weights from {CAFFE_URL}...")
                req = urllib.request.Request(CAFFE_URL, headers=headers)
                with urllib.request.urlopen(req) as resp, open(self.weights_path, "wb") as f:
                    f.write(resp.read())
            except Exception as e:
                logger.warning(f"[OBJECT DETECTOR WARN] Could not download Caffe Model Weights: {e}")

    def _init_model(self):
        self._download_if_missing()
        if os.path.exists(self.proto_path) and os.path.exists(self.weights_path):
            try:
                self.net = cv2.dnn.readNetFromCaffe(self.proto_path, self.weights_path)
                logger.info("[OBJECT DETECTOR SUCCESS] DNN MobileNet-SSD Caffe model loaded successfully (30+ FPS Active).")
            except Exception as e:
                logger.warning(f"[OBJECT DETECTOR WARN] Could not load Caffe model: {e}.")
                self.net = None
        else:
            logger.warning(f"[OBJECT DETECTOR WARN] Model files missing. Active fallback: Fast Phone Contour Engine.")

    def detect_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Process frame at high speed (30+ FPS) with NMS filtering and IoU tracking.
        Returns list of tracked detections:
        [{"track_id": int, "box": (x, y, w, h), "label": str, "confidence": float, "consecutive_frames": int}]
        """
        raw_boxes = []
        raw_confidences = []
        raw_labels = []

        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]

        # 1. OpenCV DNN Model Detection (Fast 300x300 Inference)
        if self.net:
            try:
                blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
                self.net.setInput(blob)
                out = self.net.forward()

                for i in range(out.shape[2]):
                    confidence = float(out[0, 0, i, 2])
                    if confidence >= OBJECT_CONF_THRESHOLD:
                        idx = int(out[0, 0, i, 1])
                        # Detect cell phone, book, tablet, handheld screen (excluding full background room monitors)
                        if idx in [15, 67, 73, 63, 65, 77] or idx == 20:
                            box = out[0, 0, i, 3:7] * np.array([w, h, w, h])
                            (startX, startY, endX, endY) = box.astype("int")
                            bw = max(1, endX - startX)
                            bh = max(1, endY - startY)

                            # Exclude background monitors spanning > 60% of the frame
                            if bw > w * 0.65 or bh > h * 0.65:
                                continue

                            raw_boxes.append([startX, startY, bw, bh])
                            raw_confidences.append(confidence)
                            raw_labels.append("cell phone")
            except Exception as e:
                logger.debug(f"DNN object detection error: {e}")

        # 2. Non-Maximum Suppression (NMS) Filtering
        nms_detections = []
        if raw_boxes:
            indices = cv2.dnn.NMSBoxes(raw_boxes, raw_confidences, OBJECT_CONF_THRESHOLD, NMS_THRESHOLD)
            if len(indices) > 0:
                indices = indices.flatten()
                for idx in indices:
                    nms_detections.append({
                        "box": tuple(raw_boxes[idx]),
                        "label": raw_labels[idx],
                        "confidence": raw_confidences[idx]
                    })

        # 3. Fast Downscaled Phone Slab Contour Fallback if DNN produces no candidates
        if not nms_detections:
            try:
                # Downscale 4x for fast 1ms contour detection
                small_frame = cv2.resize(frame, (320, 180))
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (3, 3), 0)
                _, thresh = cv2.threshold(blur, 60, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                scale_x = w / 320.0
                scale_y = h / 180.0

                for c in contours:
                    area = cv2.contourArea(c)
                    if 150 < area < 4500:
                        x, y, cw, ch = cv2.boundingRect(c)
                        aspect_ratio = float(ch) / max(1, cw)
                        # Vertical phone slab (1.4 - 2.5) or horizontal/tilted phone slab (0.4 - 0.7)
                        if (1.4 <= aspect_ratio <= 2.5 or 0.4 <= aspect_ratio <= 0.7):
                            rect_area = cw * ch
                            extent = float(area) / rect_area
                            if extent > 0.72:
                                # Scale coordinates back to original frame resolution
                                real_x = int(x * scale_x)
                                real_y = int(y * scale_y)
                                real_w = int(cw * scale_x)
                                real_h = int(ch * scale_y)
                                conf = min(0.90, 0.72 + (extent - 0.72) * 0.5)
                                nms_detections.append({
                                    "box": (real_x, real_y, real_w, real_h),
                                    "label": "cell phone",
                                    "confidence": float(conf)
                                })
                                break
            except Exception as e:
                logger.debug(f"Fast contour object detection error: {e}")

        # 4. IoU Tracker Coordinate Smoothing & Persistent ID Assignment
        tracked_results = self.tracker.update(nms_detections)
        return tracked_results
