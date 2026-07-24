"""
Central Configuration & Tuning Thresholds for AI Proctoring Engine.
"""

import os
import numpy as np

# Camera Resolution & Discovery Configuration
CAM_W = 1280
CAM_H = 720
PROCESS_EVERY_N = 2
CAMERA_INDEXES = [0, 1, 2, 3, 4]
VERIFICATION_WINDOW_SEC = 3.0

# Feature Toggles
ENABLE_HANDS = True
ENABLE_OBJECT_DETECTION = True
ENABLE_AUDIO = True

# Directories & Output Files
SNAPSHOT_DIR = "snapshots"
CSV_FILE = "proctor_log.csv"
REPORT_FILE = "proctor_report.html"

# Object Detection Model Paths & Classes
MODEL_PROTO_PATH = "mobile_net_ssd.prototxt"
MODEL_WEIGHTS_PATH = "mobile_net_ssd.caffemodel"
COCO_CLASSES = {
    67: "cell phone", 73: "book", 63: "laptop", 65: "remote", 64: "mouse", 66: "keyboard"
}

# Audio Configuration
AUDIO_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_BLOCK_MS = 200
TTS_RATE = 155

# Scoring Windows & Alarm Thresholds
EVENT_WINDOW = 12.0  # Sliding window duration in seconds
ALARM_MEDIUM = 15.0  # Medium risk alert threshold
ALARM_HIGH = 28.0    # High risk critical alert threshold

# Gaze & Iris Thresholds
GLANCE_THRESHOLD = 0.18  # Normalized iris center deviation
GLANCE_SUSTAIN = 1.0     # Seconds required for offscreen trigger
RAPID_SCAN_VELOCITY = 0.45

# Head Pose Thresholds & Model Geometry
YAW_THRESHOLD = 20.0
YAW_FULLTURN = 38.0
PITCH_THRESHOLD = 18.0
PITCH_LAP_GLANCE = 20.0

MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye outer corner
    (225.0, 170.0, -135.0),      # Right eye outer corner
    (-150.0, -150.0, -125.0),    # Left mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float64)

# Drowsiness / Eye Aspect Ratio (EAR)
EAR_CLOSED_THRESH = 0.15
EAR_CLOSED_SUSTAIN = 1.5

# Hand & Phone Proxy
HAND_FACE_DIST_RATIO = 0.50
HAND_SUSTAIN = 0.7

# Audio & Voice Correlation
MOUTH_OPEN_THRESHOLD = 0.14
AUDIO_RMS_THRESHOLD = 0.015
VAD_WINDOW = 0.6

# Violation Risk Scoring Weights
WEIGHT_PHONE_DETECTED = 15
WEIGHT_WINDOW_SWITCH = 10
WEIGHT_MULTIFACE = 10
WEIGHT_FULLTURN = 9
WEIGHT_OTHERVOICE = 8
WEIGHT_OCCLUSION = 7
WEIGHT_LAP_GLANCE = 7
WEIGHT_HAND_NEAR = 6
WEIGHT_RAPID_SCAN = 5
WEIGHT_SCREEN_GLOW = 5
WEIGHT_OFFSCREEN = 4
WEIGHT_HEADTURN = 4
WEIGHT_EYES_CLOSED = 4

# MediaPipe Indexing
LEFT_IRIS_IDX = [474, 475, 476, 477]
RIGHT_IRIS_IDX = [469, 470, 471, 472]
MOUTH_TOP_BOTTOM = [13, 14]
HP_IDX = [1, 152, 33, 263, 61, 291]  # Nose tip, chin, eye outer corners, mouth corners
