"""
Pydantic Data Models for Telemetry & Detection Payloads.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class GazeTelemetry(BaseModel):
    gaze_direction: str = "CENTER"
    offscreen: bool = False
    rapid_scan: bool = False
    dx: float = 0.0
    dy: float = 0.0

class HeadPoseTelemetry(BaseModel):
    head_status: str = "NORMAL"
    headturn: bool = False
    fullturn: bool = False
    lap_glance: bool = False
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0

class TelemetryPayload(BaseModel):
    risk: float = 0.0
    severity: str = "NORMAL"
    looking_left: bool = False
    looking_right: bool = False
    looking_up: bool = False
    looking_down: bool = False
    gaze_direction: str = "CENTER"
    face_detected: bool = True
    multiple_faces: bool = False
    occlusion: bool = False
    phone_detected: bool = False
    head_turned: bool = False
    lap_glance: bool = False
    blink_count: int = 0
    fps: float = 0.0
    event: Optional[str] = None
    active_window: str = "Exam Window"
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    timestamp: str = ""
