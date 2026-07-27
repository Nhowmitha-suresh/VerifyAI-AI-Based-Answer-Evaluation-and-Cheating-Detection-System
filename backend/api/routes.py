"""
REST API Endpoints for AI Proctoring Web Application.
Handles routes for dashboard, MJPEG video feed, health, status, risk, events,
snapshots, HTML report, and session control actions.
"""

import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from typing import Dict, Any

from backend.core.settings import settings
from backend.core.logger import logger
from backend.core.app_state import app_state
from backend.services.webcam_service import webcam_service
from backend.services.risk_service import risk_engine
from backend.services.snapshot_service import snapshot_service
from backend.services.calibration_service import calibration_service
from backend.services.report_service import report_service

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def get_dashboard_page():
    """Serve the modern Glassmorphic Tailwind CSS proctoring dashboard."""
    dash_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "index.html")
    if not os.path.exists(dash_path):
        dash_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dashboard.html")
    if os.path.exists(dash_path):
        with open(dash_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>VerifyAI Proctoring System Online</h1><p>Frontend template initializing...</p>"

@router.get("/video_feed")
def video_feed():
    """Real-time MJPEG camera stream endpoint."""
    return StreamingResponse(
        webcam_service.get_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/health")
@router.get("/api/health")
def health_check() -> Dict[str, Any]:
    """System health check endpoint."""
    return {
        "status": "ONLINE",
        "system": settings.APP_NAME,
        "version": settings.VERSION,
        "active": app_state.session_active,
        "camera_running": webcam_service.is_running
    }

@router.get("/status")
def get_status() -> Dict[str, Any]:
    """Detailed exam session status response."""
    return {
        "session_active": app_state.session_active,
        "session_paused": app_state.session_paused,
        "exam_duration_sec": round(app_state.get_duration(), 1),
        "fps": app_state.current_fps,
        "current_risk": app_state.risk_score,
        "peak_risk": app_state.peak_risk_score,
        "severity": app_state.severity,
        "blink_count": app_state.blink_count,
        "total_events": len(app_state.events),
        "calibration_status": app_state.calibration_status,
        "active_window": app_state.telemetry_data.get("active_window", "Exam Window"),
        "system_health": app_state.get_system_stats()
    }

@router.get("/risk")
def get_risk() -> Dict[str, Any]:
    """Get live risk score and severity status."""
    return {
        "current_risk": app_state.risk_score,
        "peak_risk": app_state.peak_risk_score,
        "severity": app_state.severity,
        "explanation": f"Current risk level is {app_state.severity} ({app_state.risk_score}%)."
    }

@router.get("/events")
def get_events(limit: int = 50) -> Dict[str, Any]:
    """Get list of logged incident events."""
    return {"total": len(app_state.events), "events": app_state.events[-limit:]}

@router.get("/snapshots")
def get_snapshots() -> Dict[str, Any]:
    """Get evidence snapshots gallery."""
    return {"total": len(app_state.snapshots), "snapshots": app_state.snapshots}

@router.get("/report", response_class=HTMLResponse)
def get_report():
    """Generate and return self-contained HTML audit report."""
    report_file = report_service.generate_html_report()
    if os.path.exists(report_file):
        with open(report_file, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="Proctor report not generated yet.")

# Control Action Endpoints
@router.post("/start")
def start_session() -> Dict[str, str]:
    app_state.reset_session()
    webcam_service.start()
    return {"status": "OK", "message": "Proctoring session started."}

@router.post("/stop")
def stop_session() -> Dict[str, str]:
    app_state.session_active = False
    webcam_service.stop()
    report_service.generate_html_report()
    return {"status": "OK", "message": "Proctoring session stopped & report generated."}

@router.post("/pause")
def pause_session() -> Dict[str, str]:
    app_state.session_paused = True
    return {"status": "OK", "message": "Proctoring session paused."}

@router.post("/resume")
def resume_session() -> Dict[str, str]:
    app_state.session_paused = False
    return {"status": "OK", "message": "Proctoring session resumed."}

@router.post("/snapshot")
def manual_snapshot() -> Dict[str, Any]:
    with webcam_service.lock:
        frame = webcam_service.current_frame
    if frame is not None:
        res = snapshot_service.capture_snapshot(frame, reason="manual")
        if res:
            return {"status": "OK", "snapshot": res}
    raise HTTPException(status_code=400, detail="Webcam frame unavailable.")

@router.post("/recalibrate")
def recalibrate_gaze() -> Dict[str, str]:
    calibration_service.set_calibration((0.5, 0.5))
    return {"status": "OK", "message": "Gaze baseline recalibrated to center (0.5, 0.5)."}

@router.post("/reset-risk")
def reset_risk_score() -> Dict[str, str]:
    risk_engine.reset()
    return {"status": "OK", "message": "Risk score reset to 0.0."}
