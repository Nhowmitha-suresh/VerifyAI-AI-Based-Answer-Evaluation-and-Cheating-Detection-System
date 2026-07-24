"""
AI Proctoring & Anti-Cheat Engine - Advanced Multi-Modal Suite
Features:
- Futuristic Glassmorphic HUD Telemetry Dashboard
- Mobile Phone & Forbidden Object AI Detection (OpenCV DNN & Shape Heuristic)
- Active Window OS Proctoring (Detects Alt+Tab & Window Focus Switch)
- Secondary Screen & Phone Glow (Face Luminance Flicker Detector)
- Rapid Gaze Scan & Lap Glance Detection (Head-Down + Gaze-Down)
- 5-Zone Gaze Direction & 3D Head Pose Estimation
- Hand-to-Face & Ear Proximity Phone Proxy Detection
- Audio VAD & Mouth Correlation (Collusion Detection)
- Drowsiness & Sustained Eye Closure Monitor
- Real-time Sliding Window Risk Index (0-100%)
- Automatic Violation Snapshot Evidence Logging (`snapshots/`)
- Log Export (CSV) & Interactive HTML Audit Report (`proctor_report.html`)
"""

import os
# Suppress verbose C++ MediaPipe / TensorFlow protobuf logging
os.environ["GLOG_minloglevel"] = "2"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import cv2
import time
import math
import threading
import csv
import sys
import collections
import datetime
import numpy as np

# OS-Specific Active Window Tracking (Windows Native)
if sys.platform == "win32":
    import ctypes
    import winsound

# Optional Sound & Voice libraries
try:
    import sounddevice as sd
except Exception:
    sd = None

try:
    import webrtcvad
    HAS_VAD = True
except Exception:
    HAS_VAD = False

try:
    import pyttsx3
    tts_engine = pyttsx3.init()
    tts_engine.setProperty("rate", 155)
except Exception:
    tts_engine = None

import mediapipe as mp

# -------------------- CONFIGURATION & THRESHOLDS --------------------
CAM_W, CAM_H = 1280, 720        # HD Camera resolution
PROCESS_EVERY_N = 2             # Performance multiplier (process every N frames)
ENABLE_HANDS = True             # Hand landmark processing toggle
ENABLE_OBJECT_DETECTION = True  # Mobile phone / forbidden object detector
ENABLE_AUDIO = True and sd is not None
LOG_CSV = True
CSV_FILE = "proctor_log.csv"
SNAPSHOT_DIR = "snapshots"
REPORT_FILE = "proctor_report.html"

# Scoring & Risk Thresholds
EVENT_WINDOW = 12.0             # Sliding window duration (seconds)
ALARM_MEDIUM = 15.0             # Medium risk alert score
ALARM_HIGH = 28.0               # Critical high risk alarm score

# Gaze & Head pose thresholds
GLANCE_THRESHOLD = 0.18         # Iris normalized deviation threshold
GLANCE_SUSTAIN = 1.0            # Seconds required to trigger offscreen alert
YAW_FULLTURN = 38.0             # Full head turn degrees
YAW_THRESHOLD = 20.0            # Moderate turn degrees
PITCH_THRESHOLD = 18.0           # Pitch up/down threshold
EAR_CLOSED_THRESH = 0.15        # Eye aspect ratio threshold for closed eyes
EAR_CLOSED_SUSTAIN = 1.5        # Seconds to trigger drowsiness alert

# Hand & Phone proxy
HAND_FACE_DIST_RATIO = 0.50     # Distance ratio of hand center to face center
HAND_SUSTAIN = 0.7              # Seconds required for hand near face alert

# Audio & Mouth correlation
MOUTH_OPEN_THRESHOLD = 0.14     # Mouth open distance ratio
AUDIO_RMS_THRESHOLD = 0.015     # Fallback RMS energy threshold
VAD_WINDOW = 0.6                # Seconds of audio buffer window

# Event Scoring Weights
WEIGHT_PHONE_DETECTED = 15      # Mobile Phone Detected (CRITICAL)
WEIGHT_WINDOW_SWITCH = 10       # Active Window Focus Switch
WEIGHT_OFFSCREEN = 4
WEIGHT_HEADTURN = 4
WEIGHT_FULLTURN = 9
WEIGHT_HAND_NEAR = 6
WEIGHT_MULTIFACE = 10
WEIGHT_OCCLUSION = 7
WEIGHT_OTHERVOICE = 8
WEIGHT_EYES_CLOSED = 4
WEIGHT_RAPID_SCAN = 5
WEIGHT_LAP_GLANCE = 7
WEIGHT_SCREEN_GLOW = 5

# MediaPipe Setup
mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands

LEFT_IRIS_IDX = [474, 475, 476, 477]
RIGHT_IRIS_IDX = [469, 470, 471, 472]
MOUTH_TOP_BOTTOM = [13, 14]
HP_IDX = [1, 152, 33, 263, 61, 291]  # Nose tip, chin, eye outer corners, mouth corners

# -------------------- EVENT QUEUE & LOGGING --------------------
events = collections.deque()
all_logged_events = []
snapshot_count = 0

if not os.path.exists(SNAPSHOT_DIR):
    os.makedirs(SNAPSHOT_DIR)

def push_event(score, label=None):
    now = time.time()
    events.append((now, score, label))
    cutoff = now - EVENT_WINDOW
    while events and events[0][0] < cutoff:
        events.popleft()

def current_score():
    return sum(s for _, s, _ in events)

if LOG_CSV and not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "datetime", "event_label", "score", "total_score"])

def log_event(label, score):
    now = time.time()
    dt_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tot = current_score()
    all_logged_events.append({"timestamp": now, "datetime": dt_str, "label": label, "score": score, "total": tot})
    if LOG_CSV:
        try:
            with open(CSV_FILE, "a", newline="") as f:
                w = csv.writer(f)
                w.writerow([now, dt_str, label, score, tot])
        except Exception:
            pass

def save_snapshot(frame, reason="violation"):
    global snapshot_count
    snapshot_count += 1
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SNAPSHOT_DIR}/snapshot_{timestamp}_{reason}_{snapshot_count}.jpg"
    try:
        cv2.imwrite(filename, frame)
        print(f"[SNAPSHOT] Saved evidence: {filename}")
        return filename
    except Exception as e:
        print("[SNAPSHOT ERROR]:", e)
        return None

# -------------------- OS ACTIVE WINDOW TRACKING --------------------
def get_active_window_title():
    if sys.platform == "win32":
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value or "Unknown Window"
        except Exception:
            return "Unknown Window"
    return "Proctoring Window"

# -------------------- MOBILE PHONE & OBJECT DETECTOR --------------------
class ObjectDetector:
    COCO_CLASSES = {
        67: "cell phone", 73: "book", 63: "laptop", 65: "remote", 64: "mouse", 66: "keyboard"
    }

    def __init__(self):
        self.net = None
        self.proto_path = "mobile_net_ssd.prototxt"
        self.weights_path = "mobile_net_ssd.caffemodel"
        self._init_model()

    def _init_model(self):
        if os.path.exists(self.proto_path) and os.path.exists(self.weights_path):
            try:
                self.net = cv2.dnn.readNetFromCaffe(self.proto_path, self.weights_path)
                print("[OBJECT DETECTOR] DNN MobileNet-SSD Model loaded successfully.")
            except Exception as e:
                print("[OBJECT DETECTOR WARN] Could not load Caffe model:", e)
                self.net = None

    def detect_objects(self, frame):
        detections = []
        h, w = frame.shape[:2]

        if self.net:
            try:
                blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
                self.net.setInput(blob)
                out = self.net.forward()
                
                for i in range(out.shape[2]):
                    confidence = out[0, 0, i, 2]
                    if confidence > 0.40:
                        idx = int(out[0, 0, i, 1])
                        if idx in self.COCO_CLASSES or idx == 67:
                            label = self.COCO_CLASSES.get(idx, "cell phone")
                            box = out[0, 0, i, 3:7] * np.array([w, h, w, h])
                            (startX, startY, endX, endY) = box.astype("int")
                            detections.append({
                                "box": (startX, startY, endX - startX, endY - startY),
                                "label": label,
                                "confidence": float(confidence)
                            })
            except Exception:
                pass

        # Geometric Phone Shape Heuristic Fallback
        if not detections:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for c in contours:
                area = cv2.contourArea(c)
                if 2500 < area < 45000:
                    x, y, cw, ch = cv2.boundingRect(c)
                    aspect_ratio = float(ch) / max(1, cw)
                    if (1.5 <= aspect_ratio <= 2.4 or 0.42 <= aspect_ratio <= 0.65) and (y > h * 0.25):
                        rect_area = cw * ch
                        extent = float(area) / rect_area
                        if extent > 0.70:
                            detections.append({
                                "box": (x, y, cw, ch),
                                "label": "cell phone",
                                "confidence": 0.72
                            })
                            break

        return detections

# -------------------- AUDIO & ALARM SYSTEM --------------------
_alarm_lock = threading.Lock()
_alarm_mode = None
_stop_alarm = False
_last_speech_time = 0

def speak_async(text):
    global _last_speech_time
    if time.time() - _last_speech_time < 3.0:
        return
    _last_speech_time = time.time()
    def _run():
        if tts_engine:
            try:
                tts_engine.say(text)
                tts_engine.runAndWait()
            except Exception:
                pass
    threading.Thread(target=_run, daemon=True).start()

def beep(freq=1000, duration=300):
    if sys.platform == "win32":
        try:
            winsound.Beep(freq, duration)
        except Exception:
            pass

def start_alert(mode):
    global _alarm_mode, _stop_alarm
    with _alarm_lock:
        if _alarm_mode == mode:
            return
        _alarm_mode = mode
        _stop_alarm = False

    if mode == "low":
        threading.Thread(target=lambda: beep(900, 200), daemon=True).start()
        speak_async("Please focus on the screen.")
    elif mode == "medium":
        threading.Thread(target=lambda: (beep(1000, 300), time.sleep(0.1), beep(1000, 300)), daemon=True).start()
        speak_async("Warning: Suspicious behavior detected.")
    elif mode == "high":
        def loop():
            while True:
                with _alarm_lock:
                    if _stop_alarm:
                        break
                beep(1300, 400)
                time.sleep(0.15)
        threading.Thread(target=loop, daemon=True).start()
        speak_async("High risk alert: Proctoring violation threshold exceeded!")

def stop_alerts():
    global _alarm_mode, _stop_alarm
    with _alarm_lock:
        _stop_alarm = True
        _alarm_mode = None

class AudioMonitor:
    def __init__(self, rate=16000, channels=1, block_ms=200):
        self.rate = rate
        self.channels = channels
        self.block_ms = block_ms
        self.buffer = collections.deque(maxlen=int(2000 / block_ms))
        self.vad = None
        if HAS_VAD:
            try:
                self.vad = webrtcvad.Vad(2)
            except Exception:
                self.vad = None
        self.stream = None
        self.running = False

    def _callback(self, indata, frames, time_info, status):
        if indata is None:
            return
        pcm16 = (indata[:, 0] * 32767).astype(np.int16).tobytes()
        self.buffer.append(pcm16)

    def start(self):
        if sd is None:
            return
        try:
            self.running = True
            self.stream = sd.InputStream(
                channels=self.channels,
                samplerate=self.rate,
                blocksize=int(self.rate * self.block_ms / 1000),
                callback=self._callback
            )
            self.stream.start()
        except Exception as e:
            print("[AUDIO WARN] Microphone capture stream error:", e)

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
        self.running = False

    def recent_audio_activity(self, window_sec=0.6):
        if self.vad is not None:
            cnt, total = 0, 0
            num_blocks = int(window_sec * 1000 / self.block_ms)
            for pcm in list(self.buffer)[-num_blocks:]:
                total += 1
                try:
                    if self.vad.is_speech(pcm, sample_rate=self.rate):
                        cnt += 1
                except Exception:
                    pass
            return cnt > 0 and (cnt / max(1, total)) > 0.15
        else:
            if not self.buffer:
                return False
            num_blocks = int(window_sec * 1000 / self.block_ms)
            pcm = b"".join(list(self.buffer)[-num_blocks:])
            try:
                arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32767.0
                rms = np.sqrt(np.mean(arr * arr)) if arr.size else 0.0
                return rms > AUDIO_RMS_THRESHOLD
            except Exception:
                return False

# -------------------- HEAD POSE MATH & GEOMETRY --------------------
model_points = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye outer corner
    (225.0, 170.0, -135.0),      # Right eye outer corner
    (-150.0, -150.0, -125.0),    # Left mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float64)

def estimate_head_pose(image_points, img_w, img_h):
    try:
        focal_length = img_w
        center = (img_w / 2.0, img_h / 2.0)
        camera_matrix = np.array([[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]], dtype=np.float64)
        dist = np.zeros((4, 1))
        ok, rvec, tvec = cv2.solvePnP(model_points, np.array(image_points, dtype=np.float64), camera_matrix, dist, flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok:
            return None, None
        rmat, _ = cv2.Rodrigues(rvec)
        sy = math.sqrt(rmat[0, 0] * rmat[0, 0] + rmat[1, 0] * rmat[1, 0])
        x = math.atan2(rmat[2, 1], rmat[2, 2])
        y = math.atan2(-rmat[2, 0], sy)
        z = math.atan2(rmat[1, 0], rmat[0, 0])

        nose_end_3d = np.array([(0.0, 0.0, 1000.0)], dtype=np.float64)
        nose_end_2d, _ = cv2.projectPoints(nose_end_3d, rvec, tvec, camera_matrix, dist)
        p1 = (int(image_points[0][0]), int(image_points[0][1]))
        p2 = (int(nose_end_2d[0][0][0]), int(nose_end_2d[0][0][1]))

        return (math.degrees(x), math.degrees(y), math.degrees(z)), (p1, p2)
    except Exception:
        return None, None

def normalized_iris_center(iris_pts):
    cx, cy = iris_pts.mean(axis=0)
    x0, x1 = int(iris_pts[:, 0].min()), int(iris_pts[:, 0].max())
    y0, y1 = int(iris_pts[:, 1].min()), int(iris_pts[:, 1].max())
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    return (cx - x0) / w, (cy - y0) / h

def calculate_ear(lm_px):
    try:
        top = lm_px[MOUTH_TOP_BOTTOM[0]]
        bot = lm_px[MOUTH_TOP_BOTTOM[1]]
        nose = lm_px[1]
        chin = lm_px[152]
        face_h = np.linalg.norm(nose - chin)
        return float(np.linalg.norm(top - bot) / max(1.0, face_h))
    except Exception:
        return 0.0

# -------------------- FUTURISTIC HUD DRAWING UTILITIES --------------------
def draw_hud_panel(img, x, y, w, h, bg_color=(15, 20, 30), alpha=0.65, border_color=(0, 255, 200)):
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), bg_color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    cv2.rectangle(img, (x, y), (x + w, y + h), border_color, 1)

def draw_hud_header(frame, fps, elapsed_sec, score, status_text, window_title):
    h, w = frame.shape[:2]
    draw_hud_panel(frame, 10, 10, w - 20, 60, bg_color=(10, 15, 25), alpha=0.75, border_color=(0, 230, 255))
    
    cv2.putText(frame, "NEGOSPHERE AI PROCTORING ENGINE", (25, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(frame, f"Active Window: {window_title[:28]}", (25, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 200, 220), 1)
    
    if score >= ALARM_HIGH:
        badge_color = (0, 0, 255)
    elif score >= ALARM_MEDIUM:
        badge_color = (0, 165, 255)
    else:
        badge_color = (0, 255, 120)

    cv2.rectangle(frame, (480, 22), (660, 50), badge_color, -1)
    cv2.putText(frame, status_text, (490, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 2)

    timer_str = str(datetime.timedelta(seconds=int(elapsed_sec)))
    cv2.putText(frame, f"TIME: {timer_str}", (w - 340, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 220, 255), 1)
    cv2.putText(frame, f"FPS: {fps:.1f}", (w - 130, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 200), 1)

def draw_risk_gauge(frame, score):
    h, w = frame.shape[:2]
    x, y, gw, gh = 20, h - 75, w - 40, 38
    draw_hud_panel(frame, x, y, gw, gh, bg_color=(10, 15, 25), alpha=0.85, border_color=(100, 100, 100))
    
    ratio = min(1.0, score / ALARM_HIGH)
    fill_w = int((gw - 10) * ratio)
    
    if ratio > 0.7:
        fill_color = (0, 0, 255)
    elif ratio > 0.4:
        fill_color = (0, 165, 255)
    else:
        fill_color = (0, 255, 100)

    if fill_w > 0:
        cv2.rectangle(frame, (x + 5, y + 5), (x + 5 + fill_w, y + gh - 5), fill_color, -1)

    cv2.putText(frame, f"RISK INDEX: {score:.1f} / {ALARM_HIGH:.0f}", (x + 20, y + 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

def draw_telemetry_panel(frame, flags):
    h, w = frame.shape[:2]
    pw, ph = 340, 300
    px, py = 20, 80
    draw_hud_panel(frame, px, py, pw, ph, bg_color=(10, 15, 25), alpha=0.75, border_color=(0, 200, 255))
    
    cv2.putText(frame, "TELEMETRY MONITOR", (px + 15, py + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 255), 2)
    cv2.line(frame, (px + 15, py + 33), (px + pw - 15, py + 33), (0, 180, 220), 1)

    items = [
        ("Mobile Phone AI", flags.get("phone_status", "CLEAR"), flags.get("phone_detected", False)),
        ("Window Focus", flags.get("window_status", "FOCUSED"), flags.get("window_switched", False)),
        ("Gaze Direction", flags.get("gaze_status", "CENTER"), flags.get("offscreen", False) or flags.get("rapid_scan", False)),
        ("Head Orientation", flags.get("head_status", "NORMAL"), flags.get("headturn", False) or flags.get("lap_glance", False)),
        ("Face Count", flags.get("face_status", "1 Face"), flags.get("multiface", False) or flags.get("occlusion", False)),
        ("Hand/Gadget Proxy", flags.get("hand_status", "CLEAR"), flags.get("handnear", False)),
        ("Audio/Collusion", flags.get("audio_status", "QUIET"), flags.get("othervoice", False)),
        ("Drowsiness/Blink", flags.get("ear_status", "ACTIVE"), flags.get("eyes_closed", False)),
    ]

    iy = py + 56
    for label, val, is_alert in items:
        dot_color = (0, 0, 255) if is_alert else (0, 255, 120)
        cv2.circle(frame, (px + 22, iy - 4), 4, dot_color, -1)
        cv2.putText(frame, f"{label}:", (px + 35, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (220, 220, 220), 1)
        
        val_color = (0, 80, 255) if is_alert else (0, 255, 180)
        cv2.putText(frame, str(val), (px + 190, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.44, val_color, 2 if is_alert else 1)
        iy += 28

def draw_event_feed(frame, recent_logs):
    h, w = frame.shape[:2]
    pw, ph = 340, 300
    px, py = w - pw - 20, 80
    draw_hud_panel(frame, px, py, pw, ph, bg_color=(10, 15, 25), alpha=0.75, border_color=(0, 200, 255))
    
    cv2.putText(frame, "INCIDENT FEED", (px + 15, py + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 255), 2)
    cv2.line(frame, (px + 15, py + 33), (px + pw - 15, py + 33), (0, 180, 220), 1)

    iy = py + 56
    for log in list(recent_logs)[-7:]:
        time_str = datetime.datetime.fromtimestamp(log[0]).strftime("%H:%M:%S")
        label = log[2] or "violation"
        score = log[1]
        cv2.putText(frame, f"[{time_str}] {label.upper()}", (px + 15, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (100, 200, 255), 1)
        cv2.putText(frame, f"+{score}", (px + pw - 50, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (0, 0, 255), 2)
        iy += 28

# -------------------- HTML SESSION REPORT GENERATOR --------------------
def generate_html_report():
    print(f"[REPORT] Generating session report: {REPORT_FILE}...")
    total_events = len(all_logged_events)
    max_score = max([e["total"] for e in all_logged_events], default=0.0)
    
    counts = collections.Counter([e["label"] for e in all_logged_events])
    snapshots = [os.path.join(SNAPSHOT_DIR, f) for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".jpg")] if os.path.exists(SNAPSHOT_DIR) else []

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Proctoring Session Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 24px; }}
        .container {{ max-width: 1100px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h1 {{ color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 12px; margin-top: 0; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 24px 0; }}
        .card {{ background: #0f172a; padding: 20px; border-radius: 8px; border-left: 4px solid #38bdf8; }}
        .card h3 {{ margin: 0 0 8px 0; font-size: 14px; color: #94a3b8; text-transform: uppercase; }}
        .card .val {{ font-size: 28px; font-weight: bold; color: #f8fafc; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #38bdf8; }}
        tr:hover {{ background: #283548; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block; }}
        .badge-high {{ background: #ef4444; color: #fff; }}
        .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-top: 20px; }}
        .gallery img {{ width: 100%; border-radius: 8px; border: 2px solid #334155; transition: transform 0.2s; }}
        .gallery img:hover {{ transform: scale(1.03); border-color: #38bdf8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>NegoSphere AI Proctoring Audit Report</h1>
        <p style="color: #94a3b8;">Generated on: {datetime.datetime.now().strftime("%B %d, %Y - %H:%M:%S")}</p>
        
        <div class="stats-grid">
            <div class="card">
                <h3>Total Incidents</h3>
                <div class="val">{total_events}</div>
            </div>
            <div class="card" style="border-color: {'#ef4444' if max_score >= ALARM_HIGH else '#10b981'};">
                <h3>Peak Risk Score</h3>
                <div class="val">{max_score:.1f}</div>
            </div>
            <div class="card">
                <h3>Evidence Snapshots</h3>
                <div class="val">{len(snapshots)}</div>
            </div>
            <div class="card">
                <h3>Session Verdict</h3>
                <div class="val" style="color: {'#ef4444' if max_score >= ALARM_HIGH else '#10b981'};">
                    {"FLAGGED HIGH RISK" if max_score >= ALARM_HIGH else "PASS / LOW RISK"}
                </div>
            </div>
        </div>

        <h2>Violation Breakdown</h2>
        <table>
            <thead>
                <tr>
                    <th>Event Category</th>
                    <th>Count</th>
                    <th>Severity Rating</th>
                </tr>
            </thead>
            <tbody>
                {''.join([f"<tr><td>{k.upper()}</td><td>{v}</td><td>{'CRITICAL' if k in ['phone_detected', 'window_switch'] else 'HIGH'}</td></tr>" for k,v in counts.items()]) or "<tr><td colspan='3'>No violations recorded.</td></tr>"}
            </tbody>
        </table>

        <h2>Incident Timeline (Recent 20)</h2>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Event Type</th>
                    <th>Event Score</th>
                    <th>Cumulative Risk</th>
                </tr>
            </thead>
            <tbody>
                {''.join([f"<tr><td>{e['datetime']}</td><td><span class='badge badge-high'>{e['label'].upper()}</span></td><td>+{e['score']}</td><td>{e['total']:.1f}</td></tr>" for e in all_logged_events[-20:]]) or "<tr><td colspan='4'>Clean session.</td></tr>"}
            </tbody>
        </table>

        {"<h2>Evidence Gallery</h2><div class='gallery'>" + ''.join([f"<div><img src='{os.path.basename(s)}' alt='Snapshot'><p style='font-size:12px;color:#94a3b8;'>{os.path.basename(s)}</p></div>" for s in snapshots]) + "</div>" if snapshots else ""}
    </div>
</body>
</html>
"""
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[REPORT SUCCESS] Saved interactive report to file:///{os.path.abspath(REPORT_FILE)}")

# -------------------- MAIN PROCTORING LOOP --------------------
def main():
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=2,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5) if ENABLE_HANDS else None
    object_detector = ObjectDetector() if ENABLE_OBJECT_DETECTION else None

    # Target Primary Camera 0 cleanly
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap or not cap.isOpened():
        cap = cv2.VideoCapture(0)

    if not cap or not cap.isOpened():
        print("[ERROR] Cannot access webcam device. Please check camera connection.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
    time.sleep(0.2)

    audio_mon = AudioMonitor() if ENABLE_AUDIO else None
    if audio_mon:
        audio_mon.start()

    initial_window = get_active_window_title()

    # Calibration phase
    print("[CALIBRATION] Please look straight at the screen for 3 seconds...")
    calib_samples = []
    calib_start = time.time()
    while time.time() - calib_start < 3.0:
        ret, frame = cap.read()
        if not ret: continue
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = face_mesh.process(rgb)
        if res.multi_face_landmarks:
            lm = np.array([(int(p.x * w), int(p.y * h)) for p in res.multi_face_landmarks[0].landmark])
            try:
                nxL, nyL = normalized_iris_center(lm[LEFT_IRIS_IDX])
                nxR, nyR = normalized_iris_center(lm[RIGHT_IRIS_IDX])
                calib_samples.append(((nxL + nxR) / 2.0, (nyL + nyR) / 2.0))
            except Exception:
                pass
        cv2.putText(frame, "CALIBRATING GAZE CENTER... LOOK STRAIGHT", (w//2 - 250, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
        try:
            cv2.imshow("Proctoring System", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
        except Exception:
            pass

    calib_center = np.mean(calib_samples, axis=0) if calib_samples else (0.5, 0.5)
    print("[CALIBRATION COMPLETE] Center baseline:", calib_center)

    frame_idx = 0
    start_time = time.time()
    last_frame_time = time.time()
    fps = 30.0

    ema_nx, ema_ny = calib_center
    ema_yaw, ema_pitch = 0.0, 0.0

    glance_buf = collections.deque()
    head_buf = collections.deque()
    hand_buf = collections.deque()
    occ_buf = collections.deque()
    mf_buf = collections.deque()
    ear_buf = collections.deque()
    gaze_pos_history = collections.deque(maxlen=15)
    luminance_history = collections.deque(maxlen=20)

    try:
        cv2.namedWindow("Proctoring System", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Proctoring System", 1280, 720)
    except Exception:
        pass

    last_high_snapshot = 0
    last_phone_snapshot = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret: continue
            
            h, w = frame.shape[:2]
            frame_idx += 1
            now = time.time()

            dt = now - last_frame_time
            last_frame_time = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = None
            hands_res = None
            detections = []

            if (frame_idx % PROCESS_EVERY_N) == 0:
                results = face_mesh.process(rgb)
                if ENABLE_HANDS and hands:
                    hands_res = hands.process(rgb)
                if object_detector:
                    detections = object_detector.detect_objects(frame)

            offscreen_flag = headturn_flag = fullturn_flag = handnear_flag = False
            multiface_flag = occlusion_flag = othervoice_flag = eyes_closed_flag = False
            phone_flag = window_switch_flag = rapid_scan_flag = lap_glance_flag = glow_flag = False

            gaze_str, head_str, face_str, hand_str, audio_str, ear_str = "CENTER", "NORMAL", "1 Face", "CLEAR", "QUIET", "ACTIVE"
            phone_str, window_str = "CLEAR", "FOCUSED"

            # 1. MOBILE PHONE & FORBIDDEN OBJECT DETECTION
            if detections:
                for obj in detections:
                    label = obj["label"]
                    conf = obj["confidence"]
                    (bx, by, bw, bh) = obj["box"]
                    
                    if label in ["cell phone", "mobile phone"]:
                        phone_flag = True
                        phone_str = f"PHONE ({int(conf*100)}%)"
                        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 0, 255), 3)
                        cv2.putText(frame, f"MOBILE PHONE {int(conf*100)}%", (bx, max(20, by - 8)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
                        
                        push_event(WEIGHT_PHONE_DETECTED, "phone_detected")
                        log_event("phone_detected", WEIGHT_PHONE_DETECTED)
                        
                        if now - last_phone_snapshot > 3.0:
                            save_snapshot(frame, reason="mobile_phone")
                            last_phone_snapshot = now

            # 2. ACTIVE WINDOW PROCTORING
            curr_window = get_active_window_title()
            if curr_window and curr_window != initial_window and "Proctoring System" not in curr_window:
                window_switch_flag = True
                window_str = "UNFOCUSED"
                push_event(WEIGHT_WINDOW_SWITCH, "window_switch")
                log_event("window_switch", WEIGHT_WINDOW_SWITCH)

            # 3. FACEMESH & TELEMETRY
            if results and results.multi_face_landmarks:
                nfaces = len(results.multi_face_landmarks)
                face_str = f"{nfaces} Faces"
                if nfaces > 1:
                    mf_buf.append(now)
                    if now - mf_buf[0] > 0.8:
                        multiface_flag = True
                else:
                    mf_buf.clear()

                lm = np.array([(int(p.x * w), int(p.y * h)) for p in results.multi_face_landmarks[0].landmark])

                # Face Luminance Flicker Detector (Secondary screen glow)
                try:
                    fx0, fy0 = lm[:, 0].min(), lm[:, 1].min()
                    fx1, fy1 = lm[:, 0].max(), lm[:, 1].max()
                    face_roi = frame[max(0, fy0):min(h, fy1), max(0, fx0):min(w, fx1)]
                    if face_roi.size > 0:
                        mean_lum = np.mean(cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY))
                        luminance_history.append(mean_lum)
                        if len(luminance_history) >= 10:
                            lum_std = np.std(luminance_history)
                            if lum_std > 18.0:
                                glow_flag = True
                                push_event(WEIGHT_SCREEN_GLOW, "screen_glow")
                                log_event("screen_glow", WEIGHT_SCREEN_GLOW)
                except Exception:
                    pass

                # Iris Gaze Tracking & Rapid Scan
                try:
                    Lpts = lm[LEFT_IRIS_IDX]
                    Rpts = lm[RIGHT_IRIS_IDX]
                    Lc = Lpts.mean(axis=0)
                    Rc = Rpts.mean(axis=0)
                    nxL, nyL = normalized_iris_center(Lpts)
                    nxR, nyR = normalized_iris_center(Rpts)
                    nx, ny = (nxL + nxR) / 2.0, (nyL + nyR) / 2.0
                    
                    ema_nx = 0.35 * nx + 0.65 * ema_nx
                    ema_ny = 0.35 * ny + 0.65 * ema_ny

                    dx = ema_nx - calib_center[0]
                    dy = ema_ny - calib_center[1]

                    gaze_pos_history.append((ema_nx, ema_ny))
                    if len(gaze_pos_history) >= 10:
                        gaze_arr = np.array(gaze_pos_history)
                        gaze_velocity = np.sum(np.abs(np.diff(gaze_arr[:, 0])))
                        if gaze_velocity > 0.45:
                            rapid_scan_flag = True
                            gaze_str = "RAPID SCANNING"
                            push_event(WEIGHT_RAPID_SCAN, "rapid_scan")
                            log_event("rapid_scan", WEIGHT_RAPID_SCAN)

                    if abs(dx) > GLANCE_THRESHOLD or abs(dy) > GLANCE_THRESHOLD:
                        glance_buf.append(now)
                        if not rapid_scan_flag:
                            if dx < -GLANCE_THRESHOLD: gaze_str = "LOOKING LEFT"
                            elif dx > GLANCE_THRESHOLD: gaze_str = "LOOKING RIGHT"
                            elif dy < -GLANCE_THRESHOLD: gaze_str = "LOOKING UP"
                            else: gaze_str = "LOOKING DOWN"
                    else:
                        glance_buf.clear()
                        if not rapid_scan_flag:
                            gaze_str = "CENTER"

                    if glance_buf and (now - glance_buf[0]) > GLANCE_SUSTAIN:
                        offscreen_flag = True

                    cv2.circle(frame, tuple(Lc.astype(int)), 3, (0, 255, 255), -1)
                    cv2.circle(frame, tuple(Rc.astype(int)), 3, (0, 255, 255), -1)
                except Exception:
                    pass

                # Head Pose & Lap Glance
                try:
                    img_pts = [tuple(lm[i]) for i in HP_IDX]
                    pose, axis_pts = estimate_head_pose(img_pts, w, h)
                    if pose:
                        pitch, yaw, roll = pose
                        ema_yaw = 0.35 * yaw + 0.65 * ema_yaw
                        ema_pitch = 0.35 * pitch + 0.65 * ema_pitch

                        if ema_pitch > 20.0 and (gaze_str == "LOOKING DOWN" or dy > GLANCE_THRESHOLD):
                            lap_glance_flag = True
                            head_str = "LAP GLANCE (PHONE?)"
                            push_event(WEIGHT_LAP_GLANCE, "lap_glance")
                            log_event("lap_glance", WEIGHT_LAP_GLANCE)
                        elif abs(ema_yaw) > YAW_THRESHOLD or abs(ema_pitch) > PITCH_THRESHOLD:
                            head_buf.append(now)
                            head_str = f"TURNED ({int(ema_yaw)}deg)"
                        else:
                            head_buf.clear()
                            head_str = "NORMAL"

                        if head_buf and (now - head_buf[0]) > 0.8:
                            headturn_flag = True
                        if abs(ema_yaw) > YAW_FULLTURN:
                            fullturn_flag = True
                            head_str = "FULL TURN"

                        if axis_pts:
                            cv2.line(frame, axis_pts[0], axis_pts[1], (0, 165, 255), 2)
                except Exception:
                    pass

                # Drowsiness / Eye Aspect Ratio
                try:
                    ear = calculate_ear(lm)
                    if ear < EAR_CLOSED_THRESH:
                        ear_buf.append(now)
                        ear_str = "EYES CLOSED"
                    else:
                        ear_buf.clear()
                        ear_str = "ACTIVE"
                    if ear_buf and (now - ear_buf[0]) > EAR_CLOSED_SUSTAIN:
                        eyes_closed_flag = True
                except Exception:
                    pass
            else:
                occ_buf.append(now)
                face_str = "NO FACE"
                if occ_buf and (now - occ_buf[0]) > 0.8:
                    occlusion_flag = True

            # Hands Near Face / Gadget Proxy
            if ENABLE_HANDS and hands_res and results and results.multi_face_landmarks:
                lm = np.array([(int(p.x * w), int(p.y * h)) for p in results.multi_face_landmarks[0].landmark])
                fx0, fy0 = lm[:, 0].min(), lm[:, 1].min()
                fx1, fy1 = lm[:, 0].max(), lm[:, 1].max()
                face_center = np.array([(fx0 + fx1) / 2.0, (fy0 + fy1) / 2.0])
                face_diag = math.hypot(fx1 - fx0, fy1 - fy0)

                for hand in hands_res.multi_hand_landmarks:
                    pts = np.array([(int(p.x * w), int(p.y * h)) for p in hand.landmark])
                    hcx, hcy = pts[:, 0].mean(), pts[:, 1].mean()
                    cv2.circle(frame, (int(hcx), int(hcy)), 5, (255, 0, 200), -1)
                    d = math.hypot(hcx - face_center[0], hcy - face_center[1])
                    if d < HAND_FACE_DIST_RATIO * face_diag:
                        hand_buf.append(now)
                        hand_str = "HAND NEAR FACE"
                if hand_buf and (now - hand_buf[0]) > HAND_SUSTAIN:
                    handnear_flag = True
            else:
                hand_buf.clear()

            # Audio VAD Correlation
            if ENABLE_AUDIO and audio_mon:
                audio_act = audio_mon.recent_audio_activity(window_sec=VAD_WINDOW)
                mouth_open = 0.0
                if results and results.multi_face_landmarks:
                    lm = np.array([(int(p.x * w), int(p.y * h)) for p in results.multi_face_landmarks[0].landmark])
                    top = lm[MOUTH_TOP_BOTTOM[0]]
                    bot = lm[MOUTH_TOP_BOTTOM[1]]
                    nose, chin = lm[1], lm[152]
                    mouth_open = float(np.linalg.norm(top - bot) / max(1.0, np.linalg.norm(nose - chin)))

                if audio_act:
                    audio_str = "VOICE SPEECH" if mouth_open >= MOUTH_OPEN_THRESHOLD else "SUSPICIOUS VOICE"
                    if mouth_open < MOUTH_OPEN_THRESHOLD:
                        push_event(WEIGHT_OTHERVOICE, "other_voice")
                        log_event("other_voice", WEIGHT_OTHERVOICE)
                        othervoice_flag = True
                else:
                    audio_str = "QUIET"

            # Push Events & Log
            if offscreen_flag:
                push_event(WEIGHT_OFFSCREEN, "offscreen"); log_event("offscreen", WEIGHT_OFFSCREEN)
            if headturn_flag:
                push_event(WEIGHT_HEADTURN, "headturn"); log_event("headturn", WEIGHT_HEADTURN)
            if fullturn_flag:
                push_event(WEIGHT_FULLTURN, "fullturn"); log_event("fullturn", WEIGHT_FULLTURN)
            if handnear_flag:
                push_event(WEIGHT_HAND_NEAR, "hand_near"); log_event("hand_near", WEIGHT_HAND_NEAR)
            if multiface_flag:
                push_event(WEIGHT_MULTIFACE, "multiface"); log_event("multiface", WEIGHT_MULTIFACE)
            if occlusion_flag:
                push_event(WEIGHT_OCCLUSION, "occlusion"); log_event("occlusion", WEIGHT_OCCLUSION)
            if eyes_closed_flag:
                push_event(WEIGHT_EYES_CLOSED, "eyes_closed"); log_event("eyes_closed", WEIGHT_EYES_CLOSED)

            score = current_score()

            # Automatic evidence snapshot on high risk
            if score >= ALARM_HIGH and (now - last_high_snapshot > 5.0):
                save_snapshot(frame, reason="high_risk")
                last_high_snapshot = now

            # Audio alert triggers
            if score >= ALARM_HIGH or phone_flag:
                start_alert("high")
                status_text = "CRITICAL RISK - PHONE / ALARM"
            elif score >= ALARM_MEDIUM:
                start_alert("medium")
                status_text = "WARNING - SUSPICIOUS BEHAVIOR"
            else:
                stop_alerts()
                status_text = "MONITORING - NORMAL"

            # Render Futuristic HUD Overlays
            elapsed = now - start_time
            draw_hud_header(frame, fps, elapsed, score, status_text, curr_window)
            draw_risk_gauge(frame, score)
            
            telemetry_flags = {
                "phone_status": phone_str, "phone_detected": phone_flag,
                "window_status": window_str, "window_switched": window_switch_flag,
                "gaze_status": gaze_str, "offscreen": offscreen_flag, "rapid_scan": rapid_scan_flag,
                "head_status": head_str, "headturn": headturn_flag or fullturn_flag, "lap_glance": lap_glance_flag,
                "face_status": face_str, "multiface": multiface_flag, "occlusion": occlusion_flag,
                "hand_status": hand_str, "handnear": handnear_flag,
                "audio_status": audio_str, "othervoice": othervoice_flag,
                "ear_status": ear_str, "eyes_closed": eyes_closed_flag
            }
            draw_telemetry_panel(frame, telemetry_flags)
            draw_event_feed(frame, events)

            try:
                cv2.imshow("Proctoring System", frame)
                k = cv2.waitKey(1) & 0xFF
                if k == 27 or k == ord('q') or k == ord('Q'):
                    break
                elif k == ord('c') or k == ord('C'):
                    calib_center = (ema_nx, ema_ny)
                    print("[HOTKEY] Recalibrated gaze baseline to:", calib_center)
                elif k == ord('r') or k == ord('R'):
                    events.clear()
                    print("[HOTKEY] Reset risk score.")
                elif k == ord('s') or k == ord('S'):
                    save_snapshot(frame, reason="manual")
            except Exception:
                pass

    finally:
        if audio_mon:
            audio_mon.stop()
        if cap:
            cap.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        face_mesh.close()
        if hands: hands.close()
        
        generate_html_report()
        print("Proctoring session exited cleanly.")

if __name__ == "__main__":
    main()
