"""
Multi-Modal Computer Vision & AI Detection Service.
Orchestrates MediaPipe FaceMesh, MediaPipe Hands, 3D Head Pose solvePnP,
and OpenCV DNN MobileNet-SSD Object Detector.
"""

import cv2
import time
import math
import numpy as np
import mediapipe as mp
from typing import Dict, Any, List, Tuple, Optional

from backend.core.settings import settings
from backend.core.logger import logger
from backend.services.gaze_service import GazeService

# Define MediaPipe indices
HP_IDX = [1, 152, 33, 263, 61, 291]
MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye outer corner
    (225.0, 170.0, -135.0),      # Right eye outer corner
    (-150.0, -150.0, -125.0),    # Left mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float64)

def compute_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
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
        self.box = np.array(box, dtype=np.float32)
        self.confidence = confidence
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.consecutive_frames = 1
        self.stale_frames = 0

    def update(self, new_box: Tuple[int, int, int, int], confidence: float, alpha: float = 0.4):
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
                new_track = TrackedObject(self.next_track_id, det_label, det_box, det_conf)
                self.next_track_id += 1
                self.tracks.append(new_track)

        self.tracks = [t for t in self.tracks if t.stale_frames < self.max_stale]
        return [t.to_dict() for t in self.tracks]

class ObjectDetectorService:
    def __init__(self):
        self.net = None
        self.proto_path = settings.MODEL_PROTO_PATH
        self.weights_path = settings.MODEL_WEIGHTS_PATH
        self.tracker = IoUTracker(iou_threshold=0.30, max_stale=4)
        self._init_model()

    def _init_model(self):
        import os
        if os.path.exists(self.proto_path) and os.path.exists(self.weights_path):
            try:
                self.net = cv2.dnn.readNetFromCaffe(self.proto_path, self.weights_path)
                logger.info("[OBJECT DETECTOR] Caffe MobileNet-SSD loaded successfully.")
            except Exception as e:
                logger.warning(f"[OBJECT DETECTOR] Could not load Caffe model: {e}")

    def detect_objects(self, frame: np.ndarray, hand_boxes: List[Tuple[int, int, int, int]] = None) -> List[Dict[str, Any]]:
        if frame is None:
            return []
        h, w = frame.shape[:2]
        raw_detections = []

        # 1. DNN Object Detection (MobileNet-SSD)
        if self.net is not None:
            try:
                blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
                self.net.setInput(blob)
                out = self.net.forward()
                for i in range(out.shape[2]):
                    confidence = float(out[0, 0, i, 2])
                    if confidence >= settings.OBJECT_CONF_THRESHOLD:
                        idx = int(out[0, 0, i, 1])
                        # Detect TV/monitor (class 20 in VOC), person (15), or cell phone (67, 77 in COCO)
                        if idx in [15, 20, 67, 73, 63, 65, 77]:
                            box = out[0, 0, i, 3:7] * np.array([w, h, w, h])
                            startX, startY, endX, endY = box.astype("int")
                            bw = max(1, endX - startX)
                            bh = max(1, endY - startY)
                            if bw > w * 0.65 or bh > h * 0.65:
                                continue
                            # If class is person (15), only include if small rectangular aspect near hands
                            if idx == 15 and not (1.3 <= bh / max(1, bw) <= 2.8 or 0.35 <= bh / max(1, bw) <= 0.75):
                                continue
                            raw_detections.append({
                                "box": (startX, startY, bw, bh),
                                "label": "cell phone",
                                "confidence": confidence
                            })
            except Exception as e:
                logger.debug(f"Object detection error: {e}")

        # 2. Handheld Rectangular Contour Fallback Detection
        if not raw_detections:
            try:
                small = cv2.resize(frame, (320, 180))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                _, thresh = cv2.threshold(blur, 55, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                scale_x, scale_y = w / 320.0, h / 180.0
                
                for c in contours:
                    area = cv2.contourArea(c)
                    if 180 < area < 6500:
                        x, y, cw, ch = cv2.boundingRect(c)
                        aspect = float(ch) / max(1, cw)
                        rect_area = cw * ch
                        extent = float(area) / max(1.0, rect_area)
                        
                        # Typical phone aspect ratio ranges (portrait 1.4-2.8, landscape 0.35-0.7)
                        if (1.35 <= aspect <= 2.8 or 0.35 <= aspect <= 0.72) and extent > 0.70:
                            real_x, real_y = int(x * scale_x), int(y * scale_y)
                            real_w, real_h = int(cw * scale_x), int(ch * scale_y)
                            
                            # Check if contour overlaps or sits near hands if available
                            conf = 0.82
                            if hand_boxes:
                                for hx, hy, hw, hh in hand_boxes:
                                    if compute_iou((real_x, real_y, real_w, real_h), (hx, hy, hw, hh)) > 0.05:
                                        conf = 0.92
                                        break
                                        
                            raw_detections.append({
                                "box": (real_x, real_y, real_w, real_h),
                                "label": "cell phone",
                                "confidence": conf
                            })
                            break
            except Exception:
                pass

        tracked_results = self.tracker.update(raw_detections)
        return tracked_results

class MultiModalDetector:
    def __init__(self):
        self.gaze_service = GazeService()
        self.object_detector = ObjectDetectorService()
        
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.hands = mp.solutions.hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.5
        ) if settings.ENABLE_HANDS else None

        self.ema_yaw = 0.0
        self.ema_pitch = 0.0

    def process_frame(self, frame: np.ndarray, now: float) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process frame through MediaPipe Face Mesh, Head Pose solvePnP, Gaze Tracker, Facial Expression, and Object Detector.
        Annotates frame with HUD overlays and returns comprehensive telemetry dictionary.
        """
        if frame is None or frame.size == 0:
            return frame, {}

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        mesh_res = self.face_mesh.process(rgb)
        
        # Hand tracking
        hand_boxes = []
        if self.hands is not None:
            try:
                hand_res = self.hands.process(rgb)
                if hand_res and hand_res.multi_hand_landmarks:
                    for h_lm in hand_res.multi_hand_landmarks:
                        h_pts = np.array([(int(l.x * w), int(l.y * h)) for l in h_lm.landmark])
                        min_x, min_y = h_pts.min(axis=0)
                        max_x, max_y = h_pts.max(axis=0)
                        hand_boxes.append((int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y)))
                        # Draw hand outline
                        cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), (255, 165, 0), 1)
            except Exception:
                pass

        face_detected = False
        multiface = False
        occlusion = False
        headturn, fullturn, lap_glance = False, False, False
        head_status = "NORMAL"
        pitch, yaw, roll = 0.0, 0.0, 0.0

        # Facial Expression Telemetry
        expression = "NEUTRAL"
        mar = 0.0
        talking = False
        yawning = False
        smiling = False

        gaze_telemetry = {
            "gaze_direction": "CENTER", "looking_left": False, "looking_right": False,
            "looking_up": False, "looking_down": False, "offscreen": False, "rapid_scan": False,
            "dx": 0.0, "dy": 0.0, "ear": 0.3, "eyes_closed": False, "blink_count": 0,
            "Lc": (0, 0), "Rc": (0, 0)
        }

        if mesh_res and mesh_res.multi_face_landmarks:
            num_faces = len(mesh_res.multi_face_landmarks)
            if num_faces > 1:
                multiface = True
            face_detected = True
            
            # Primary Candidate Face
            landmarks = mesh_res.multi_face_landmarks[0].landmark
            lm_px = np.array([(int(l.x * w), int(l.y * h)) for l in landmarks])

            # 1. Gaze Tracking
            gaze_telemetry = self.gaze_service.process(lm_px, now)
            
            # Draw Pupil Crosshairs on Frame
            Lc = gaze_telemetry.get("Lc", (0, 0))
            Rc = gaze_telemetry.get("Rc", (0, 0))
            if Lc[0] > 0 and Lc[1] > 0:
                cv2.circle(frame, Lc, 3, (255, 255, 0), -1)
            if Rc[0] > 0 and Rc[1] > 0:
                cv2.circle(frame, Rc, 3, (255, 255, 0), -1)

            # 2. Facial Expression Analysis (Mouth Aspect Ratio & Smile Ratio)
            try:
                top_lip = lm_px[13]
                bot_lip = lm_px[14]
                l_mouth = lm_px[61]
                r_mouth = lm_px[291]
                nose = lm_px[1]
                chin = lm_px[152]

                mouth_h = float(np.linalg.norm(top_lip - bot_lip))
                mouth_w = float(np.linalg.norm(l_mouth - r_mouth))
                face_h = float(np.linalg.norm(nose - chin))

                mar = round(mouth_h / max(1.0, mouth_w), 2)
                smile_ratio = round(mouth_w / max(1.0, face_h), 2)

                if mar > 0.45:
                    expression = "YAWNING / MOUTH OPEN"
                    yawning = True
                elif mar > 0.22:
                    expression = "TALKING / SPEAKING"
                    talking = True
                elif smile_ratio > 0.45:
                    expression = "SMILING"
                    smiling = True

                # Draw Lip Contour HUD
                cv2.line(frame, tuple(top_lip), tuple(bot_lip), (0, 255, 0) if not talking else (0, 165, 255), 2)
                cv2.line(frame, tuple(l_mouth), tuple(r_mouth), (0, 255, 0) if not smiling else (255, 0, 255), 2)
            except Exception:
                pass

            # 3. 3D Head Pose solvePnP Estimation
            try:
                img_pts = np.array([tuple(lm_px[i]) for i in HP_IDX], dtype=np.float64)
                focal_length = w
                center = (w / 2.0, h / 2.0)
                cam_matrix = np.array([[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]], dtype=np.float64)
                dist_coeffs = np.zeros((4, 1))

                ok, rvec, tvec = cv2.solvePnP(MODEL_POINTS, img_pts, cam_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
                if ok:
                    rmat, _ = cv2.Rodrigues(rvec)
                    sy = math.sqrt(rmat[0, 0] * rmat[0, 0] + rmat[1, 0] * rmat[1, 0])
                    x_deg = math.degrees(math.atan2(rmat[2, 1], rmat[2, 2]))
                    y_deg = math.degrees(math.atan2(-rmat[2, 0], sy))
                    z_deg = math.degrees(math.atan2(rmat[1, 0], rmat[0, 0]))

                    self.ema_yaw = 0.35 * y_deg + 0.65 * self.ema_yaw
                    self.ema_pitch = 0.35 * x_deg + 0.65 * self.ema_pitch

                    pitch, yaw, roll = self.ema_pitch, self.ema_yaw, z_deg

                    if self.ema_pitch > settings.PITCH_LAP_GLANCE and (gaze_telemetry["looking_down"] or gaze_telemetry["dy"] > 0.18):
                        lap_glance = True
                        head_status = "LAP GLANCE (PHONE?)"
                    elif abs(self.ema_yaw) > settings.YAW_FULLTURN:
                        fullturn = True
                        head_status = "FULL TURN"
                    elif abs(self.ema_yaw) > settings.YAW_THRESHOLD or abs(self.ema_pitch) > settings.PITCH_THRESHOLD:
                        headturn = True
                        head_status = f"TURNED ({int(self.ema_yaw)}deg)"

                    # Nose projection axis line
                    nose_end_3d = np.array([(0.0, 0.0, 1000.0)], dtype=np.float64)
                    nose_end_2d, _ = cv2.projectPoints(nose_end_3d, rvec, tvec, cam_matrix, dist_coeffs)
                    p1 = (int(img_pts[0][0]), int(img_pts[0][1]))
                    p2 = (int(nose_end_2d[0][0][0]), int(nose_end_2d[0][0][1]))
                    cv2.arrowedLine(frame, p1, p2, (0, 255, 255), 2, cv2.LINE_AA, tipLength=0.2)
            except Exception:
                pass

        # 4. Object Detection (Cell Phone)
        phone_detected = False
        detected_objects = self.object_detector.detect_objects(frame, hand_boxes=hand_boxes)
        if detected_objects:
            phone_detected = True
            for det in detected_objects:
                x, y, bw, bh = det["box"]
                cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 0, 255), 3)
                cv2.rectangle(frame, (x, max(0, y - 25)), (x + bw, y), (0, 0, 255), -1)
                cv2.putText(frame, f"CELL PHONE {int(det['confidence']*100)}%", (x + 5, max(15, y - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # 5. Top HUD Banner Annotations
        cv2.putText(frame, f"GAZE: {gaze_telemetry['gaze_direction']}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, f"EXPRESSION: {expression}", (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if expression == "NEUTRAL" else (0, 165, 255), 2)

        telemetry = {
            "face_detected": face_detected,
            "multiface": multiface,
            "occlusion": occlusion,
            "gaze_direction": gaze_telemetry["gaze_direction"],
            "looking_left": gaze_telemetry["looking_left"],
            "looking_right": gaze_telemetry["looking_right"],
            "looking_up": gaze_telemetry["looking_up"],
            "looking_down": gaze_telemetry["looking_down"],
            "offscreen": gaze_telemetry["offscreen"],
            "rapid_scan": gaze_telemetry["rapid_scan"],
            "eyes_closed": gaze_telemetry["eyes_closed"],
            "blink_count": gaze_telemetry["blink_count"],
            "head_status": head_status,
            "headturn": headturn,
            "fullturn": fullturn,
            "lap_glance": lap_glance,
            "pitch": round(pitch, 1),
            "yaw": round(yaw, 1),
            "roll": round(roll, 1),
            "expression": expression,
            "mar": mar,
            "talking": talking,
            "yawning": yawning,
            "smiling": smiling,
            "phone_detected": phone_detected
        }

        return frame, telemetry

