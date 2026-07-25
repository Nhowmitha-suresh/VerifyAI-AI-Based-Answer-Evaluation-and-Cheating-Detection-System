"""
Intelligent Behavioral Risk Engine & Explainable AI Module.
Context-aware multi-signal risk correlation, time-weighted score decay, and AI explainability.
"""

import time
import collections
from typing import Dict, List, Any
from .config import (
    ALARM_MEDIUM, ALARM_HIGH,
    WEIGHT_PHONE_DETECTED, WEIGHT_WINDOW_SWITCH, WEIGHT_OFFSCREEN,
    WEIGHT_HEADTURN, WEIGHT_FULLTURN, WEIGHT_HAND_NEAR, WEIGHT_MULTIFACE,
    WEIGHT_OCCLUSION, WEIGHT_OTHERVOICE, WEIGHT_EYES_CLOSED, WEIGHT_RAPID_SCAN,
    WEIGHT_LAP_GLANCE
)
from .logger import logger, push_event, log_event


class BehavioralRiskEngine:
    """
    Explainable AI Behavioral Engine that correlates multi-modal proctoring telemetry
    signals, applies context-aware combo multipliers, decays scores over time,
    and outputs structured human-readable explanations.
    """

    def __init__(self, decay_halflife_sec: float = 15.0):
        self.decay_halflife_sec = decay_halflife_sec
        self.last_update_time = time.time()
        self.cumulative_score = 0.0
        self.active_events = collections.deque()  # (timestamp, weight, label, explanation)
        self.event_counts = collections.Counter()
        self.last_explanation = "Normal monitoring state."
        self.current_factors: List[str] = []

    def evaluate_telemetry(self, telemetry: Dict[str, Any], now: float = None) -> Dict[str, Any]:
        """
        Evaluate frame-by-frame telemetry flags, trigger context-aware combined violations,
        decay inactive scores, and produce explainable risk output.
        """
        if now is None:
            now = time.time()

        dt = max(0.0, now - self.last_update_time)
        self.last_update_time = now

        # 1. Apply Exponential Score Decay (halflife decay on cumulative score)
        decay_factor = 0.5 ** (dt / self.decay_halflife_sec) if self.decay_halflife_sec > 0 else 1.0
        self.cumulative_score *= decay_factor

        # 2. Extract Active Telemetry Flags
        phone = telemetry.get("phone_detected", False)
        window = telemetry.get("window_switched", False)
        offscreen = telemetry.get("offscreen", False)
        rapid_scan = telemetry.get("rapid_scan", False)
        headturn = telemetry.get("headturn", False)
        fullturn = telemetry.get("fullturn", False)
        lap_glance = telemetry.get("lap_glance", False)
        multiface = telemetry.get("multiface", False)
        occlusion = telemetry.get("occlusion", False)
        handnear = telemetry.get("handnear", False)
        othervoice = telemetry.get("othervoice", False)
        eyes_closed = telemetry.get("eyes_closed", False)

        active_reasons = []
        new_score_boost = 0.0

        # 3. Context-Aware Multi-Signal Violation Combos (Highest Priority)
        if phone and lap_glance:
            weight = 40.0
            reason = "CRITICAL: Mobile phone detected while candidate is looking down at lap."
            self._add_event(now, weight, "phone_lap_combo", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        elif phone and window:
            weight = 45.0
            reason = "CRITICAL: Mobile phone detected during active window switch."
            self._add_event(now, weight, "phone_window_combo", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        elif phone:
            weight = float(WEIGHT_PHONE_DETECTED)
            reason = f"Mobile Phone detected on camera feed ({telemetry.get('phone_status', 'PHONE')})."
            self._add_event(now, weight, "phone_detected", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        if othervoice and mouth_closed_flag(telemetry):
            weight = 30.0
            reason = "HIGH: External voice detected while candidate's mouth remained closed (Collusion)."
            self._add_event(now, weight, "collusion_voice_combo", reason)
            new_score_boost += weight
            active_reasons.append(reason)
        elif othervoice:
            weight = float(WEIGHT_OTHERVOICE)
            reason = "Suspicious audio / secondary voice detected in environment."
            self._add_event(now, weight, "other_voice", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        if offscreen and rapid_scan:
            weight = 25.0
            reason = "HIGH: Rapid eye scan pattern detected while candidate looking off-screen."
            self._add_event(now, weight, "rapid_scan_offscreen_combo", reason)
            new_score_boost += weight
            active_reasons.append(reason)
        elif rapid_scan:
            weight = float(WEIGHT_RAPID_SCAN)
            reason = "Rapid eye directional scanning across off-screen region."
            self._add_event(now, weight, "rapid_scan", reason)
            new_score_boost += weight
            active_reasons.append(reason)
        elif offscreen:
            weight = float(WEIGHT_OFFSCREEN)
            reason = "Candidate looking off-screen (gaze deviation)."
            self._add_event(now, weight, "offscreen", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        if lap_glance and not (phone and lap_glance):
            weight = float(WEIGHT_LAP_GLANCE)
            reason = "Head pitch tilted down combined with downward gaze (possible lap glance)."
            self._add_event(now, weight, "lap_glance", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        if fullturn:
            weight = float(WEIGHT_FULLTURN)
            reason = "Candidate turned head completely away from screen."
            self._add_event(now, weight, "fullturn", reason)
            new_score_boost += weight
            active_reasons.append(reason)
        elif headturn:
            weight = float(WEIGHT_HEADTURN)
            reason = "Candidate turned head significantly."
            self._add_event(now, weight, "headturn", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        if window and not (phone and window):
            weight = float(WEIGHT_WINDOW_SWITCH)
            reason = f"Candidate switched active window / lost focus ({telemetry.get('window_status', 'UNFOCUSED')})."
            self._add_event(now, weight, "window_switch", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        if multiface:
            weight = float(WEIGHT_MULTIFACE)
            reason = f"Multiple faces detected in frame ({telemetry.get('face_status', '2+ Faces')})."
            self._add_event(now, weight, "multiface", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        if occlusion:
            weight = float(WEIGHT_OCCLUSION)
            reason = "Candidate face missing or occluded from camera."
            self._add_event(now, weight, "occlusion", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        if handnear:
            weight = float(WEIGHT_HAND_NEAR)
            reason = "Hand gesture / gadget proxy detected near facial region."
            self._add_event(now, weight, "hand_near", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        if eyes_closed:
            weight = float(WEIGHT_EYES_CLOSED)
            reason = "Prolonged eye closure / drowsiness threshold reached."
            self._add_event(now, weight, "eyes_closed", reason)
            new_score_boost += weight
            active_reasons.append(reason)

        # Update Cumulative Score
        if new_score_boost > 0:
            self.cumulative_score += new_score_boost

        self.current_factors = active_reasons if active_reasons else ["Candidate behavior normal and centered."]
        self.last_explanation = " | ".join(self.current_factors[:3])

        # Risk Rating
        score = self.cumulative_score
        if score >= ALARM_HIGH:
            severity = "CRITICAL"
        elif score >= ALARM_MEDIUM:
            severity = "WARNING"
        else:
            severity = "NORMAL"

        risk_pct = min(100.0, (score / ALARM_HIGH) * 100.0)

        return {
            "risk_score": round(score, 1),
            "risk_percentage": round(risk_pct, 1),
            "severity": severity,
            "active_factors": self.current_factors,
            "explanation": self.last_explanation,
            "event_boost": round(new_score_boost, 1)
        }

    def _add_event(self, timestamp: float, weight: float, label: str, reason: str):
        self.active_events.append((timestamp, weight, label, reason))
        self.event_counts[label] += 1
        push_event(weight, label)
        log_event(label, weight)


def mouth_closed_flag(telemetry: Dict[str, Any]) -> bool:
    ear_status = telemetry.get("ear_status", "")
    audio_status = telemetry.get("audio_status", "")
    return "SUSPICIOUS" in audio_status or "QUIET" in audio_status
