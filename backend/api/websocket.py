"""
WebSocket Telemetry Streaming Service.
Broadcasts real-time exam telemetry, risk score, gaze directions, system metrics,
and live incidents every 100ms to all connected web clients.
"""

import json
import asyncio
import datetime
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.core.app_state import app_state
from backend.core.logger import logger

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message_dict: dict):
        if not self.active_connections:
            return
        payload_str = json.dumps(message_dict)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload_str)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.active_connections.remove(conn)

ws_manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Telemetry Packet Broadcast Loop (~100ms interval)
            telemetry = app_state.telemetry_data.copy()
            sys_stats = app_state.get_system_stats()
            
            latest_event_desc = app_state.events[-1].get("description") if app_state.events else "Candidate behavior normal."

            phone_det = telemetry.get("phone_detected", False)
            danger = phone_det or (app_state.severity in ["CRITICAL", "HIGH_RISK"])
            danger_msg = "🚨 DANGER ALERT: CELL PHONE DETECTED IN REAL-TIME!" if phone_det else ("🚨 DANGER ALERT: HIGH RISK PROCTORING VIOLATION!" if danger else "")

            payload = {
                "risk": app_state.risk_score,
                "peak_risk": app_state.peak_risk_score,
                "severity": app_state.severity,
                "danger_alert": danger,
                "danger_message": danger_msg,
                "gaze_direction": telemetry.get("gaze_direction", "CENTER"),
                "looking_left": telemetry.get("looking_left", False),
                "looking_right": telemetry.get("looking_right", False),
                "looking_up": telemetry.get("looking_up", False),
                "looking_down": telemetry.get("looking_down", False),
                "offscreen": telemetry.get("offscreen", False),
                "rapid_scan": telemetry.get("rapid_scan", False),
                "face_detected": telemetry.get("face_detected", True),
                "multiple_faces": telemetry.get("multiface", False),
                "occlusion": telemetry.get("occlusion", False),
                "phone_detected": telemetry.get("phone_detected", False),
                "head_turned": telemetry.get("headturn", False),
                "lap_glance": telemetry.get("lap_glance", False),
                "blink_count": telemetry.get("blink_count", 0),
                "fps": app_state.current_fps,
                "event": latest_event_desc,
                "active_window": telemetry.get("active_window", "Exam Window"),
                "exam_duration_sec": round(app_state.get_duration(), 1),
                "cpu_percent": sys_stats["cpu_percent"],
                "ram_percent": sys_stats["ram_percent"],
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            }

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.1)  # Broadcast every 100ms

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
