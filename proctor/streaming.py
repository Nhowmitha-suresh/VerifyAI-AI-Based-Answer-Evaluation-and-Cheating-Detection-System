"""
Real-Time Telemetry Streaming & WebSocket Broadcaster Module.
Broadcasts candidate proctoring telemetry payloads to connected clients/dashboards.
"""

import json
import asyncio
import threading
from typing import Set, Dict, Any
from .logger import logger


class TelemetryStreamer:
    """
    Manages active WebSocket client connections and broadcasts live telemetry packets.
    """

    def __init__(self):
        self.connected_clients: Set[Any] = set()
        self._lock = threading.Lock()

    def register(self, websocket: Any):
        with self._lock:
            self.connected_clients.add(websocket)
            logger.info(f"[STREAMER] Client connected. Total active clients: {len(self.connected_clients)}")

    def unregister(self, websocket: Any):
        with self._lock:
            self.connected_clients.discard(websocket)
            logger.info(f"[STREAMER] Client disconnected. Total active clients: {len(self.connected_clients)}")

    def broadcast_sync(self, payload: Dict[str, Any]):
        """Synchronous helper to push telemetry to active websockets."""
        if not self.connected_clients:
            return
        msg = json.dumps(payload)
        with self._lock:
            to_remove = set()
            for ws in self.connected_clients:
                try:
                    if hasattr(ws, "send_text"):
                        asyncio.run_coroutine_threadsafe(ws.send_text(msg), ws.app.loop)
                except Exception as e:
                    logger.debug(f"Broadcast error: {e}")
                    to_remove.add(ws)
            self.connected_clients -= to_remove


streamer = TelemetryStreamer()
