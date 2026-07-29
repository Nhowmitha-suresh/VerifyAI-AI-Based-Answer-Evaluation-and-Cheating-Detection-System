"""
Thread-Safe Global Application State Manager.
Maintains session state, telemetry metrics, risk history, and events buffer.
"""

import time
import threading
import psutil
from typing import List, Dict, Any, Optional

class AppState:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AppState, cls).__new__(cls)
                cls._instance._init_state()
            return cls._instance

    def _init_state(self):
        self.state_lock = threading.Lock()
        self.session_active: bool = True
        self.session_paused: bool = False
        self.start_time: float = time.time()
        self.pause_time: float = 0.0
        self.total_paused_duration: float = 0.0

        self.current_fps: float = 0.0
        self.risk_score: float = 0.0
        self.peak_risk_score: float = 0.0
        self.severity: str = "NORMAL"

        self.blink_count: int = 0
        self.calibration_status: bool = True
        
        self.telemetry_data: Dict[str, Any] = {
            "gaze_direction": "CENTER",
            "offscreen": False,
            "rapid_scan": False,
            "head_status": "NORMAL",
            "headturn": False,
            "fullturn": False,
            "lap_glance": False,
            "pitch": 0.0,
            "yaw": 0.0,
            "roll": 0.0,
            "face_detected": True,
            "multiface": False,
            "occlusion": False,
            "phone_detected": False,
            "phone_status": "CLEAR",
            "hand_status": "CLEAR",
            "audio_status": "QUIET",
            "eyes_closed": False,
            "active_window": "Exam Browser",
            "window_switched": False
        }

        self.events: List[Dict[str, Any]] = []
        self.snapshots: List[Dict[str, Any]] = []
        self.latest_frame: Optional[Any] = None

    def reset_risk(self):
        with self.state_lock:
            self.risk_score = 0.0
            self.severity = "NORMAL"

    def reset_session(self):
        with self.state_lock:
            self.session_active = True
            self.session_paused = False
            self.start_time = time.time()
            self.pause_time = 0.0
            self.total_paused_duration = 0.0
            self.risk_score = 0.0
            self.peak_risk_score = 0.0
            self.severity = "NORMAL"
            self.blink_count = 0
            self.events.clear()
            self.snapshots.clear()

    def get_duration(self) -> float:
        if not self.session_active:
            return 0.0
        now = time.time()
        if self.session_paused:
            return max(0.0, self.pause_time - self.start_time - self.total_paused_duration)
        return max(0.0, now - self.start_time - self.total_paused_duration)

    def add_event(self, event_dict: Dict[str, Any]):
        with self.state_lock:
            self.events.append(event_dict)
            if len(self.events) > 500:
                self.events.pop(0)

    def add_snapshot(self, snapshot_dict: Dict[str, Any]):
        with self.state_lock:
            self.snapshots.append(snapshot_dict)

    def get_system_stats(self) -> Dict[str, float]:
        try:
            return {
                "cpu_percent": round(psutil.cpu_percent(), 1),
                "ram_percent": round(psutil.virtual_memory().percent, 1)
            }
        except Exception:
            return {"cpu_percent": 0.0, "ram_percent": 0.0}

app_state = AppState()
