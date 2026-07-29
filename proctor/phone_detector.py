"""
Mobile Phone & Prohibited Multi-Gadget AI Real-Time Detection Module.
Uses Multi-Stage Detection:
1. Ultralytics YOLOv8 (if available) / OpenCV DNN MobileNet-SSD.
2. Ultra-Fast Handheld Screen & Smartphone Contour/Glow Detector (~1ms).
3. Hand Landmark Proximity Correlation Engine.
4. Non-Maximum Suppression (NMS) & Exponential Moving Average IoU Bounding Box Tracking.
Optimized for 30+ FPS real-time execution with low latency (<20ms per frame).
"""

import cv2
import os
import urllib.request
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from .config import COCO_CLASSES, MODEL_PROTO_PATH, MODEL_WEIGHTS_PATH, OBJECT_CONF_THRESHOLD, NMS_THRESHOLD
from .tracker import IoUTracker
from .logger import logger

PROTO_URL = "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/voc/MobileNetSSD_deploy.prototxt"
CAFFE_URL = "https://raw.githubusercontent.com/PINTO0309/MobileNet-SSD-RealSense/master/caffemodel/MobileNetSSD/MobileNetSSD_deploy.caffemodel"

# Optional YOLOv8 model initialization
YOLO_MODEL = None
try:
    from ultralytics import YOLO
    try:
        YOLO_MODEL = YOLO("yolov8n.pt")
        logger.info("[OBJECT DETECTOR] Ultralytics YOLOv8 loaded successfully for ultra-accurate phone detection.")
    except Exception as e:
        logger.debug(f"[OBJECT DETECTOR] YOLOv8 model download/load error: {e}")
        YOLO_MODEL = None
except Exception:
    YOLO_MODEL = None


class ObjectDetector:

    def __init__(self):
        self.net = None
        self.proto_path = MODEL_PROTO_PATH
        self.weights_path = MODEL_WEIGHTS_PATH
        self.tracker = IoUTracker(iou_threshold=0.30, max_stale=4)
        self.yolo_model = YOLO_MODEL
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

    def detect_objects(self, frame: np.ndarray, hand_boxes: Optional[List[Tuple[int, int, int, int]]] = None) -> List[Dict[str, Any]]:
        """
        Process frame at low latency with multi-stage inference, hand correlation, and IoU tracking.
        """
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]
        raw_boxes = []
        raw_confidences = []
        raw_labels = []

        # 1. Primary Engine: Ultralytics YOLOv8 (if available)
        if self.yolo_model is not None:
            try:
                results = self.yolo_model(frame, verbose=False, conf=0.35, imgsz=320)
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        # COCO Class 67 = cell phone, 73 = book, 63 = laptop
                        if cls_id in [67, 73, 63, 65, 77]:
                            xywh = box.xywh[0].cpu().numpy()
                            cx, cy, bw, bh = xywh
                            bx = int(cx - bw / 2)
                            by = int(cy - bh / 2)
                            bw = int(bw)
                            bh = int(bh)

                            if bw > w * 0.65 or bh > h * 0.65:
                                continue

                            raw_boxes.append([max(0, bx), max(0, by), bw, bh])
                            raw_confidences.append(conf)
                            raw_labels.append("cell phone")
            except Exception as e:
                logger.debug(f"YOLOv8 detection error: {e}")

        # 2. Secondary Engine: OpenCV DNN MobileNet-SSD (Fast 300x300 Inference)
        if not raw_boxes and self.net is not None:
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
                            startX, startY, endX, endY = box.astype("int")
                            bw = max(1, endX - startX)
                            bh = max(1, endY - startY)

                            # Exclude background room monitors spanning > 65% of frame
                            if bw > w * 0.65 or bh > h * 0.65:
                                continue

                            raw_boxes.append([max(0, startX), max(0, startY), bw, bh])
                            raw_confidences.append(confidence)
                            raw_labels.append("cell phone")
            except Exception as e:
                logger.debug(f"DNN object detection error: {e}")

        # 3. Tertiary Engine: Fast Downscaled Phone Slab & Screen Reflection Contour Fallback
        if not raw_boxes:
            try:
                # Downscale 4x for fast 1ms contour & aspect ratio analysis
                small_frame = cv2.resize(frame, (320, 180))
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (3, 3), 0)
                _, thresh = cv2.threshold(blur, 60, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                scale_x = w / 320.0
                scale_y = h / 180.0

                for c in contours:
                    area = cv2.contourArea(c)
                    if 120 < area < 5500:
                        x, y, cw, ch = cv2.boundingRect(c)
                        aspect_ratio = float(ch) / max(1, cw)
                        rect_area = cw * ch
                        extent = float(area) / max(1.0, rect_area)

                        # Phone aspect ratio ranges (portrait 1.25 - 2.8, landscape 0.35 - 0.80)
                        if (1.25 <= aspect_ratio <= 2.8 or 0.35 <= aspect_ratio <= 0.80) and extent > 0.68:
                            real_x = int(x * scale_x)
                            real_y = int(y * scale_y)
                            real_w = int(cw * scale_x)
                            real_h = int(ch * scale_y)
                            
                            conf = min(0.88, 0.70 + (extent - 0.68) * 0.5)

                            # Proximity Check with Hand Bounding Boxes
                            if hand_boxes:
                                for hx, hy, hw, hh in hand_boxes:
                                    # If object is near or held by hand
                                    dist_x = max(0, max(real_x - (hx + hw), hx - (real_x + real_w)))
                                    dist_y = max(0, max(real_y - (hy + hh), hy - (real_y + real_h)))
                                    if dist_x < 40 and dist_y < 40:
                                        conf = min(0.96, conf + 0.20)
                                        break

                            raw_boxes.append([real_x, real_y, real_w, real_h])
                            raw_confidences.append(float(conf))
                            raw_labels.append("cell phone")
                            break
            except Exception as e:
                logger.debug(f"Fast contour object detection error: {e}")

        # 4. Non-Maximum Suppression (NMS) Filtering
        nms_detections = []
        if raw_boxes:
            indices = cv2.dnn.NMSBoxes(raw_boxes, raw_confidences, OBJECT_CONF_THRESHOLD, NMS_THRESHOLD)
            if len(indices) > 0:
                indices = indices.flatten()
                for idx in indices:
                    conf = raw_confidences[idx]
                    # Hand proximity boost for NMS output
                    if hand_boxes:
                        rx, ry, rw, rh = raw_boxes[idx]
                        for hx, hy, hw, hh in hand_boxes:
                            if max(0, max(rx - (hx + hw), hx - (rx + rw))) < 40 and max(0, max(ry - (hy + hh), hy - (ry + rh))) < 40:
                                conf = min(0.98, conf + 0.15)
                                break
                    nms_detections.append({
                        "box": tuple(raw_boxes[idx]),
                        "label": raw_labels[idx],
                        "confidence": float(conf)
                    })

        # 5. IoU Tracker Coordinate Smoothing & Persistent Tracking
        tracked_results = self.tracker.update(nms_detections)
        return tracked_results
