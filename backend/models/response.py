"""
Pydantic Data Models for API Responses.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class GenericResponse(BaseModel):
    status: str = "OK"
    message: str = ""

class SystemStatusResponse(BaseModel):
    session_active: bool
    session_paused: bool
    exam_duration_sec: float
    fps: float
    current_risk: float
    peak_risk: float
    severity: str
    blink_count: int
    total_events: int
    calibration_status: bool
    active_window: str
    system_health: Dict[str, float]

class RiskResponse(BaseModel):
    current_risk: float
    peak_risk: float
    severity: str
    explanation: str

class SnapshotsResponse(BaseModel):
    total: int
    snapshots: List[Dict[str, Any]]
