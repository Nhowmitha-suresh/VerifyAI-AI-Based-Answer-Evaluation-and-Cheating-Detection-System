"""
Mobile Phone & Prohibited Multi-Gadget AI Detection Module.
Uses OpenCV DNN MobileNet-SSD COCO and adaptive geometric contour heuristics to detect cell phones, books, tablets & electronic devices.
"""

import cv2
import os
import numpy as np
from typing import List, Dict, Any
from .config import COCO_CLASSES, MODEL_PROTO_PATH, MODEL_WEIGHTS_PATH
from .logger import logger


class ObjectDetector:

    def __init__(self):
        self.net = None
        self.proto_path = MODEL_PROTO_PATH
        self.weights_path = MODEL_WEIGHTS_PATH
        self._init_model()

    def _init_model(self):
        if os.path.exists(self.proto_path) and os.path.exists(self.weights_path):
            try:
                self.net = cv2.dnn.readNetFromCaffe(self.proto_path, self.weights_path)
                logger.info("[OBJECT DETECTOR] DNN MobileNet-SSD Caffe model loaded successfully.")
            except Exception as e:
                logger.warning(f"[OBJECT DETECTOR WARN] Could not load Caffe model: {e}. Falling back to contour detector.")
                self.net = None
        else:
            logger.info("[OBJECT DETECTOR INFO] Caffe weights file not found. Using geometric contour detector.")

    def detect_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Process frame and return list of detected prohibited objects:
        [{"box": (x, y, w, h), "label": str, "confidence": float}]
        """
        detections = []
        if frame is None or frame.size == 0:
            return detections

        h, w = frame.shape[:2]

        # 1. OpenCV DNN Model Detection
        if self.net:
            try:
                blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
                self.net.setInput(blob)
                out = self.net.forward()
                
                for i in range(out.shape[2]):
                    confidence = out[0, 0, i, 2]
                    if confidence > 0.35:
                        idx = int(out[0, 0, i, 1])
                        if idx in COCO_CLASSES or idx == 67 or idx == 73:
                            label = COCO_CLASSES.get(idx, "cell phone")
                            box = out[0, 0, i, 3:7] * np.array([w, h, w, h])
                            (startX, startY, endX, endY) = box.astype("int")
                            detections.append({
                                "box": (startX, startY, endX - startX, endY - startY),
                                "label": label,
                                "confidence": float(confidence)
                            })
            except Exception as e:
                logger.debug(f"DNN object detection error: {e}")

        # 2. Geometric Phone Slab / Tablet Contour Fallback
        if not detections:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for c in contours:
                    area = cv2.contourArea(c)
                    if 2500 < area < 45000:
                        x, y, cw, ch = cv2.boundingRect(c)
                        aspect_ratio = float(ch) / max(1, cw)
                        # Phone vertical/horizontal aspect ratios
                        if (1.5 <= aspect_ratio <= 2.4 or 0.42 <= aspect_ratio <= 0.65) and (y > h * 0.20):
                            rect_area = cw * ch
                            extent = float(area) / rect_area
                            if extent > 0.70:
                                detections.append({
                                    "box": (x, y, cw, ch),
                                    "label": "cell phone",
                                    "confidence": 0.75
                                })
                                break
            except Exception as e:
                logger.debug(f"Contour object detection error: {e}")

        return detections
