"""
Central Application Settings and Configuration module.
Uses Pydantic BaseSettings for type-safe environment configuration.
"""

import os
from pydantic_settings import BaseSettings
from typing import List, Dict

class Settings(BaseSettings):
    # Server Settings
    APP_NAME: str = "VerifyAI Proctoring Web Platform"
    VERSION: str = "2.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Camera & Vision Settings
    CAM_W: int = 1280
    CAM_H: int = 720
    CAMERA_INDEXES: List[int] = [0, 1, 2, 3, 4]
    PROCESS_EVERY_N: int = 2

    # Feature Toggles
    ENABLE_HANDS: bool = True
    ENABLE_OBJECT_DETECTION: bool = True
    ENABLE_AUDIO: bool = True
    ENABLE_SNAPSHOTS: bool = False

    # Directories
    SNAPSHOT_DIR: str = "snapshots"
    REPORT_DIR: str = "reports"
    LOG_DIR: str = "logs"
    CSV_FILE: str = "proctor_log.csv"
    REPORT_FILE: str = "reports/proctor_report.html"

    # Thresholds & Tuning
    FACE_CONF_THRESHOLD: float = 0.50
    OBJECT_CONF_THRESHOLD: float = 0.25
    NMS_THRESHOLD: float = 0.45

    # Risk Alert Thresholds
    ALARM_MEDIUM: float = 15.0
    ALARM_HIGH: float = 28.0

    # Gaze & Headpose Thresholds
    GLANCE_THRESHOLD: float = 0.18
    GLANCE_SUSTAIN: float = 1.0
    RAPID_SCAN_VELOCITY: float = 0.45
    YAW_THRESHOLD: float = 20.0
    YAW_FULLTURN: float = 38.0
    PITCH_THRESHOLD: float = 18.0
    PITCH_LAP_GLANCE: float = 20.0

    # Drowsiness / EAR Thresholds
    EAR_CLOSED_THRESH: float = 0.15
    EAR_CLOSED_SUSTAIN: float = 1.5

    # Model Files
    MODEL_PROTO_PATH: str = "mobile_net_ssd.prototxt"
    MODEL_WEIGHTS_PATH: str = "mobile_net_ssd.caffemodel"

    # Risk Weights
    WEIGHT_PHONE_DETECTED: float = 15.0
    WEIGHT_WINDOW_SWITCH: float = 10.0
    WEIGHT_MULTIFACE: float = 10.0
    WEIGHT_FULLTURN: float = 9.0
    WEIGHT_OTHERVOICE: float = 8.0
    WEIGHT_OCCLUSION: float = 7.0
    WEIGHT_LAP_GLANCE: float = 7.0
    WEIGHT_HAND_NEAR: float = 6.0
    WEIGHT_RAPID_SCAN: float = 5.0
    WEIGHT_SCREEN_GLOW: float = 5.0
    WEIGHT_OFFSCREEN: float = 4.0
    WEIGHT_HEADTURN: float = 4.0
    WEIGHT_EYES_CLOSED: float = 4.0

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)
os.makedirs(settings.REPORT_DIR, exist_ok=True)
os.makedirs(settings.LOG_DIR, exist_ok=True)
