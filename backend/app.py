"""
Production-Grade FastAPI Backend & Real-Time WebSockets Server.
Exposes REST APIs for sessions, incidents, analytics, and WebSocket streaming.
"""

import os
import sys
import json
import time
from typing import Dict, Any, List

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, FileResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# Add parent directory to python path for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from proctor.config import REPORT_FILE, SNAPSHOT_DIR
from proctor.logger import all_logged_events, logger
from proctor.streaming import streamer

if HAS_FASTAPI:
    app = FastAPI(
        title="NegoSphere AI Proctoring Platform API",
        description="REST & WebSockets Backend for Remote Candidate Exam Monitoring",
        version="2.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if os.path.exists(SNAPSHOT_DIR):
        app.mount("/snapshots", StaticFiles(directory=SNAPSHOT_DIR), name="snapshots")

    @app.get("/api/health")
    def health_check():
        return {"status": "ONLINE", "system": "NegoSphere AI Proctoring Engine", "timestamp": time.time()}

    @app.get("/api/session/status")
    def get_session_status():
        return {
            "active": True,
            "total_events": len(all_logged_events),
            "peak_score": max([e["total"] for e in all_logged_events], default=0.0),
            "latest_event": all_logged_events[-1] if all_logged_events else None
        }

    @app.get("/api/events")
    def get_events(limit: int = 50):
        return {"events": all_logged_events[-limit:]}

    @app.get("/api/report", response_class=HTMLResponse)
    def get_report():
        if os.path.exists(REPORT_FILE):
            with open(REPORT_FILE, "r", encoding="utf-8") as f:
                return f.read()
        raise HTTPException(status_code=404, detail="Audit report not generated yet.")

    @app.websocket("/ws/telemetry")
    async def websocket_telemetry_endpoint(websocket: WebSocket):
        await websocket.accept()
        streamer.register(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                # Keepalive / ping handling
                await websocket.send_text(json.dumps({"status": "ACK", "echo": data}))
        except WebSocketDisconnect:
            streamer.unregister(websocket)

else:
    app = None


def start_server(host: str = "0.0.0.0", port: int = 8000):
    if HAS_FASTAPI:
        logger.info(f"Starting FastAPI Proctoring Backend Server on http://{host}:{port}...")
        uvicorn.run(app, host=host, port=port)
    else:
        logger.warning("FastAPI / Uvicorn not installed. Backend server disabled.")


if __name__ == "__main__":
    start_server()
