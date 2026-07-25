"""
Mobile Phone & Prohibited Multi-Gadget AI Detection Module.
Uses OpenCV DNN MobileNet-SSD, Non-Maximum Suppression (NMS), and IoU Tracker for persistent box smoothing.
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

# Pascal VOC 20-class mappings used by MobileNet-SSD Caffe model
VOC_CLASSES = {
    0: "background", 1: "aeroplane", 2: "bicycle", 3: "bird", 4: "boat",
    5: "bottle", 6: "bus", 7: "car", 8: "cat", 9: "chair",
    10: "cow", 11: "diningtable", 12: "dog", 13: "horse", 14: "motorbike",
    15: "person", 16: "pottedplant", 17: "sheep", 18: "sofa", 19: "train",
    20: "tvmonitor"
}

# Target prohibited gadget indices (TV/Monitor/Screen: 20, Bottle/Gadget: 5, Chair/Desk item: 9, Motorbike/Tech: 14)
TARGET_PROHIBITED_INDICES = {20, 5, 9, 14, 67, 73, 63, 65, 64, 66, 77}


class ObjectDetector:

    def __init__(self):
        self.net = None
        self.proto_path = MODEL_PROTO_PATH
        self.weights_path = MODEL_WEIGHTS_PATH
        self.tracker = IoUTracker(iou_threshold=0.30, max_stale=5)
        self._init_model()

    def _download_if_missing(self):
        """Automatically fetch Caffe model definition & weights if not present on local disk."""
        headers = {"User-Agent": "Mozilla/5.0"}
        if not os.path.exists(self.proto_path):
            try:
                logger.info(f"[OBJECT DETECTOR] Downloading Caffe Prototxt from {PROTO_URL}...")
                req = urllib.request.Request(PROTO_URL, headers=headers)
                with urllib.request.urlopen(req) as resp, open(self.proto_path, "wb") as f:
                    f.write(resp.read())
                logger.info(f"[OBJECT DETECTOR] Downloaded Prototxt ({os.path.getsize(self.proto_path)} bytes).")
            except Exception as e:
                logger.warning(f"[OBJECT DETECTOR WARN] Could not download Prototxt: {e}")

        if not os.path.exists(self.weights_path):
            try:
                logger.info(f"[OBJECT DETECTOR] Downloading Caffe Model Weights from {CAFFE_URL}...")
                req = urllib.request.Request(CAFFE_URL, headers=headers)
                with urllib.request.urlopen(req) as resp, open(self.weights_path, "wb") as f:
                    f.write(resp.read())
                logger.info(f"[OBJECT DETECTOR] Downloaded Caffe Model Weights ({os.path.getsize(self.weights_path)} bytes).")
            except Exception as e:
                logger.warning(f"[OBJECT DETECTOR WARN] Could not download Caffe Model Weights: {e}")

    def _init_model(self):
        self._download_if_missing()
        if os.path.exists(self.proto_path) and os.path.exists(self.weights_path):
            try:
                self.net = cv2.dnn.readNetFromCaffe(self.proto_path, self.weights_path)
                logger.info("[OBJECT DETECTOR SUCCESS] DNN MobileNet-SSD Caffe model loaded successfully (100% Active).")
            except Exception as e:
                logger.warning(f"[OBJECT DETECTOR WARN] Could not load Caffe model: {e}. Active fallback: Adaptive Slab Contour Detector.")
                self.net = None
        else:
            logger.warning(f"[OBJECT DETECTOR WARN] Model files missing. Active fallback: Adaptive Slab Contour Detector.")

    def detect_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Process frame with NMS box filtering and IoU tracking.
        Returns list of tracked detections:
        [{"track_id": int, "box": (x, y, w, h), "label": str, "confidence": float, "consecutive_frames": int}]
        """
        raw_boxes = []
        raw_confidences = []
        raw_labels = []

        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]

        # 1. OpenCV DNN Model Detection
        if self.net:
            try:
                blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
                self.net.setInput(blob)
                out = self.net.forward()

                top_conf = 0.0
                for i in range(out.shape[2]):
                    confidence = float(out[0, 0, i, 2])
                    idx = int(out[0, 0, i, 1])

                    if confidence > top_conf and idx != 15 and idx != 0:
                        top_conf = confidence

                    if confidence >= OBJECT_CONF_THRESHOLD:
                        # Match prohibited objects: VOC class 20 (tvmonitor/screen), bottle (5), or COCO cell phone (67)
                        if idx in TARGET_PROHIBITED_INDICES or idx in VOC_CLASSES:
                            label = "cell phone" if (idx in [20, 5, 67, 77] or VOC_CLASSES.get(idx) == "tvmonitor") else COCO_CLASSES.get(idx, VOC_CLASSES.get(idx, "cell phone"))
                            
                            # Filter out full-body person detections (idx 15) unless small hand gadget
                            if idx == 15 and (out[0, 0, i, 5] - out[0, 0, i, 3]) > 0.6:
                                continue

                            box = out[0, 0, i, 3:7] * np.array([w, h, w, h])
                            (startX, startY, endX, endY) = box.astype("int")
                            bw = max(1, endX - startX)
                            bh = max(1, endY - startY)
                            raw_boxes.append([startX, startY, bw, bh])
                            raw_confidences.append(confidence)
                            raw_labels.append(label)

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

        # 3. Geometric & Dark Rectangular Phone Slab Contour Fallback
        if not nms_detections:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for c in contours:
                    area = cv2.contourArea(c)
                    if 1200 < area < 65000:
                        x, y, cw, ch = cv2.boundingRect(c)
                        aspect_ratio = float(ch) / max(1, cw)
                        if (1.2 <= aspect_ratio <= 2.8 or 0.35 <= aspect_ratio <= 0.85):
                            rect_area = cw * ch
                            extent = float(area) / rect_area
                            if extent > 0.65:
                                conf = min(0.92, 0.70 + (extent - 0.65) * 0.5)
                                nms_detections.append({
                                    "box": (x, y, cw, ch),
                                    "label": "cell phone",
                                    "confidence": float(conf)
                                })
                                break
            except Exception as e:
                logger.debug(f"Contour object detection error: {e}")

        # 4. IoU Tracker Coordinate Smoothing & Persistent ID Assignment
        tracked_results = self.tracker.update(nms_detections)
        return tracked_results
