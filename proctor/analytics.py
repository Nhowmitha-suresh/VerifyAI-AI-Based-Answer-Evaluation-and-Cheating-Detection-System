"""
Session Analytics & Aggregation Engine.
Calculates high-level candidate metrics (attention %, focus %, violation frequencies, risk profiles).
"""

import time
import collections
from typing import Dict, List, Any
from .logger import all_logged_events, logger


class SessionAnalytics:
    """
    Computes statistical summaries and analytics metrics for candidate sessions.
    """

    def __init__(self, start_time: float = None):
        self.start_time = start_time if start_time else time.time()

    def get_summary(self, gaze_analytics: Dict[str, Any] = None, incident_logs: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Compile complete candidate performance & risk metrics dict."""
        now = time.time()
        elapsed_sec = max(1.0, now - self.start_time)

        total_events = len(all_logged_events)
        scores = [e["total"] for e in all_logged_events] if all_logged_events else [0.0]
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)

        # Violation Breakdown Counts
        counts = collections.Counter([e["label"] for e in all_logged_events])

        # Gaze metrics fallback
        if not gaze_analytics:
            gaze_analytics = {
                "attention_percentage": 95.0,
                "distraction_percentage": 5.0,
                "avg_deviation": 0.08
            }

        attn_pct = gaze_analytics.get("attention_percentage", 95.0)

        # Focus Percentage calculation (100% minus window switch & offscreen penalty)
        window_switches = counts.get("window_switch", 0) + counts.get("phone_window_combo", 0)
        offscreen_events = counts.get("offscreen", 0) + counts.get("rapid_scan_offscreen_combo", 0)
        focus_penalty = min(80.0, (window_switches * 10) + (offscreen_events * 3))
        focus_pct = round(max(0.0, 100.0 - focus_penalty), 1)

        # Risk Profile Classification
        if max_score >= 28.0:
            risk_verdict = "FLAGGED HIGH RISK / HIGH VIOLATION RATE"
            verdict_code = "HIGH_RISK"
        elif max_score >= 15.0:
            risk_verdict = "SUSPICIOUS / MODERATE VIOLATION RATE"
            verdict_code = "MODERATE_RISK"
        else:
            risk_verdict = "PASSED / LOW VIOLATION RATE"
            verdict_code = "PASS"

        return {
            "elapsed_seconds": int(elapsed_sec),
            "formatted_duration": time.strftime("%H:%M:%S", time.gmtime(elapsed_sec)),
            "total_incidents": total_events,
            "recorded_video_clips": len(incident_logs) if incident_logs else 0,
            "peak_risk_score": round(max_score, 1),
            "average_risk_score": round(avg_score, 1),
            "attention_percentage": attn_pct,
            "focus_percentage": focus_pct,
            "violation_counts": dict(counts),
            "verdict": risk_verdict,
            "verdict_code": verdict_code,
            "gaze_analytics": gaze_analytics
        }
