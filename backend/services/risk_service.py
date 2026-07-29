"""
Dedicated Behavioral AI Risk Engine & Violation Scoring Service.
Computes live risk score (0-100), exponential decay, violation severity,
and automatically triggers evidence snapshot capture.
"""

import time
import datetime
import uuid
from typing import Dict, Any, List, Optional
from backend.core.settings import settings
from backend.core.logger import logger, event_logger
from backend.core.app_state import app_state
from backend.services.snapshot_service import snapshot_service

class RiskEngine:
    def __init__(self):
        self.cumulative_score: float = 0.0
        self.decay_rate: float = 0.15  # Decay per frame during normal behavior
        self.last_snapshot_time: float = 0.0
        self.snapshot_cooldown: float = 8.0  # Seconds between automated high-risk snapshots

    def reset(self):
        self.cumulative_score = 0.0
        app_state.reset_risk()

    def evaluate(self, telemetry: Dict[str, Any], frame: Optional[Any] = None) -> Dict[str, Any]:
        """
        Evaluate frame telemetry and return updated risk score, severity, and active violations.
        """
        score_increment = 0.0
        active_violations: List[str] = []

        # 1. Mobile Phone & Forbidden Gadget Detection
        if telemetry.get("phone_detected"):
            score_increment += settings.WEIGHT_PHONE_DETECTED
            active_violations.append("MOBILE PHONE DETECTED")

        # 2. Window Switch / OS Focus Loss
        if telemetry.get("window_switched"):
            score_increment += settings.WEIGHT_WINDOW_SWITCH
            active_violations.append("WINDOW SWITCH / ALT-TAB")

        # 3. Multi-Face Violation
        if telemetry.get("multiface"):
            score_increment += settings.WEIGHT_MULTIFACE
            active_violations.append("MULTIPLE PERSONS DETECTED")

        # 4. Face Absence / Occlusion
        if not telemetry.get("face_detected"):
            score_increment += settings.WEIGHT_OCCLUSION
            active_violations.append("CANDIDATE ABSENT / OCCLUDED")
        elif telemetry.get("occlusion"):
            score_increment += settings.WEIGHT_OCCLUSION
            active_violations.append("FACIAL OCCLUSION")

        # 5. Head Pose Violations
        if telemetry.get("fullturn"):
            score_increment += settings.WEIGHT_FULLTURN
            active_violations.append("FULL HEAD TURN")
        elif telemetry.get("headturn"):
            score_increment += settings.WEIGHT_HEADTURN
            active_violations.append("HEAD TURNED AWAY")

        if telemetry.get("lap_glance"):
            score_increment += settings.WEIGHT_LAP_GLANCE
            active_violations.append("HEAD PITCH DOWN / LAP GLANCE")

        # 6. Gaze Violations
        if telemetry.get("offscreen"):
            score_increment += settings.WEIGHT_OFFSCREEN
            active_violations.append("GAZE OFFSCREEN")

        if telemetry.get("rapid_scan"):
            score_increment += settings.WEIGHT_RAPID_SCAN
            active_violations.append("RAPID GAZE SCANNING")

        # 7. Eyes Closed / Prolonged Drowsiness
        if telemetry.get("eyes_closed"):
            score_increment += settings.WEIGHT_EYES_CLOSED
            active_violations.append("PROLONGED EYES CLOSED")

        # Score Adjustment: Increments or Gradual Decay
        now = time.time()
        if score_increment > 0:
            self.cumulative_score += score_increment * 0.1  # Weighted frame scale
        else:
            # Gradual decay if normal
            self.cumulative_score = max(0.0, self.cumulative_score - self.decay_rate)

        # Cap score between 0.0 and 100.0
        self.cumulative_score = min(100.0, max(0.0, self.cumulative_score))

        # Severity Classification
        if self.cumulative_score >= settings.ALARM_HIGH:
            severity = "CRITICAL"
        elif self.cumulative_score >= settings.ALARM_MEDIUM:
            severity = "HIGH_RISK"
        elif self.cumulative_score > 5.0:
            severity = "WARNING"
        else:
            severity = "NORMAL"

        # Update App State
        with app_state.state_lock:
            app_state.risk_score = round(self.cumulative_score, 1)
            app_state.peak_risk_score = max(app_state.peak_risk_score, app_state.risk_score)
            app_state.severity = severity

        # Log Significant Violations & Trigger Evidence Snapshot
        if active_violations:
            event_text = ", ".join(active_violations)
            event_id = str(uuid.uuid4())[:8]
            timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            snapshot_url = None
            if (severity in ["HIGH_RISK", "CRITICAL"] or "MOBILE PHONE DETECTED" in active_violations) and (now - self.last_snapshot_time > self.snapshot_cooldown):
                self.last_snapshot_time = now
                if frame is not None:
                    snap_res = snapshot_service.capture_snapshot(frame, reason=severity.lower())
                    if snap_res:
                        snapshot_url = snap_res.get("url")

            event_record = {
                "id": event_id,
                "timestamp": timestamp_str,
                "event_type": active_violations[0],
                "severity": severity,
                "description": f"Detected: {event_text}",
                "risk_contribution": round(score_increment, 1),
                "total_risk": round(self.cumulative_score, 1),
                "snapshot_url": snapshot_url
            }

            app_state.add_event(event_record)
            event_logger.info(f"[{severity}] Risk: {self.cumulative_score:.1f} | Events: {event_text}")

        return {
            "risk": round(self.cumulative_score, 1),
            "severity": severity,
            "violations": active_violations
        }

risk_engine = RiskEngine()
