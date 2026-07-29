"""
Asynchronous Camera Management & Telemetry Pipeline.
Handles webcam auto-discovery, multi-backend failover, health checks,
brightness validation, frozen frame detection, and structured camera state telemetry.
"""

import cv2
import time
import math
import os
import threading
import numpy as np
from typing import Generator, Optional

from backend.core.settings import settings
from backend.core.logger import logger
from backend.core.app_state import app_state
from backend.services.detector_service import MultiModalDetector
from backend.services.risk_service import risk_engine

class CameraState:
    INITIALIZING = "INITIALIZING"
    DISCOVERING_CAMERA = "DISCOVERING_CAMERA"
    REQUESTING_PERMISSION = "REQUESTING_PERMISSION"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    STREAMING = "STREAMING"
    WAITING_FOR_CANDIDATE = "WAITING_FOR_CANDIDATE"
    AI_PROCESSING = "AI_PROCESSING"
    LOW_LIGHT = "LOW_LIGHT"
    CAMERA_BUSY = "CAMERA_BUSY"
    CAMERA_DISCONNECTED = "CAMERA_DISCONNECTED"
    CAMERA_FROZEN = "CAMERA_FROZEN"
    BLACK_SCREEN = "BLACK_SCREEN"
    NO_CAMERA_FOUND = "NO_CAMERA_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    AI_ENGINE_DISCONNECTED = "AI_ENGINE_DISCONNECTED"
    WEBSOCKET_DISCONNECTED = "WEBSOCKET_DISCONNECTED"
    ERROR = "ERROR"

class WebcamService:
    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.camera_index: int = 0
        self.is_running: bool = False
        self.worker_thread: Optional[threading.Thread] = None
        
        self.detector = MultiModalDetector()
        self.current_frame: Optional[np.ndarray] = None
        self.last_external_frame_time: float = 0.0
        self.lock = threading.Lock()

        # Telemetry & Diagnostics State
        self.state: str = CameraState.INITIALIZING
        self.fps: float = 0.0
        self.frame_count: int = 0
        self.fps_start_time: float = time.time()
        
        self.brightness: float = 100.0
        self.contrast: float = 100.0
        self.black_screen_start: Optional[float] = None
        self.frozen_start: Optional[float] = None
        self.prev_frame_gray: Optional[np.ndarray] = None

    def set_external_frame(self, frame: np.ndarray):
        if frame is not None and frame.size > 0:
            with self.lock:
                self.current_frame = frame.copy()
                self.last_external_frame_time = time.time()
            with app_state.state_lock:
                app_state.latest_frame = frame.copy()

    def _discover_camera(self) -> bool:
        self.state = CameraState.DISCOVERING_CAMERA
        backends = []
        if os.name == 'nt':
            backends = [(cv2.CAP_DSHOW, "DirectShow"), (cv2.CAP_MSMF, "Media Foundation"), (cv2.CAP_ANY, "Default")]
        else:
            backends = [(cv2.CAP_ANY, "Default")]

        camera_busy_detected = False

        for idx in settings.CAMERA_INDEXES:
            for backend, backend_name in backends:
                try:
                    logger.info(f"[CAMERA DISCOVERY] Testing Index {idx} with backend {backend_name}...")
                    cap = cv2.VideoCapture(idx, backend)
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAM_W)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAM_H)
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            self.cap = cap
                            self.camera_index = idx
                            self.state = CameraState.CONNECTED
                            logger.info(f"[CAMERA SUCCESS] Opened camera index {idx} ({backend_name}).")
                            return True
                        cap.release()
                    else:
                        camera_busy_detected = True
                except Exception as e:
                    logger.debug(f"Camera open attempt exception: {e}")

        if camera_busy_detected:
            logger.warning("[CAMERA NOTICE] Camera device appears busy or owned by another process.")
            self.state = CameraState.CAMERA_BUSY
        else:
            logger.warning("[CAMERA NOTICE] No hardware webcam available.")
            self.state = CameraState.NO_CAMERA_FOUND

        return False

    def start(self):
        if self.is_running:
            return
        self.state = CameraState.INITIALIZING
        if self.cap is None or not self.cap.isOpened():
            self._discover_camera()

        self.is_running = True
        self.worker_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.worker_thread.start()
        logger.info("WebcamService frame capture thread started.")

    def stop(self):
        self.is_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        self.state = CameraState.CAMERA_DISCONNECTED
        logger.info("WebcamService stopped cleanly.")

    def _capture_loop(self):
        while self.is_running:
            if app_state.session_paused:
                time.sleep(0.1)
                continue

            # External Frame Handling (e.g. desktop proctor app)
            if time.time() - self.last_external_frame_time < 2.0:
                self.state = CameraState.STREAMING
                time.sleep(0.03)
                continue

            if self.cap is None or not self.cap.isOpened():
                self.state = CameraState.CAMERA_DISCONNECTED
                time.sleep(1.0)
                self._discover_camera()
                continue

            ret, frame = self.cap.read()
            now = time.time()

            if not ret or frame is None or frame.size == 0:
                if self.frozen_start is None:
                    self.frozen_start = now
                elif now - self.frozen_start > 2.0:
                    self.state = CameraState.CAMERA_FROZEN
                time.sleep(0.03)
                continue

            self.frozen_start = None
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Brightness & Black Screen Diagnostic
            self.brightness = float(np.mean(gray))
            if self.brightness < 5.0:
                if self.black_screen_start is None:
                    self.black_screen_start = now
                elif now - self.black_screen_start > 2.0:
                    self.state = CameraState.BLACK_SCREEN
            else:
                self.black_screen_start = None

            # Frozen Frame Diagnostic (Check consecutive frame delta)
            if self.prev_frame_gray is not None:
                delta = float(np.mean(np.abs(gray.astype(np.float32) - self.prev_frame_gray.astype(np.float32))))
                if delta < 0.1:
                    if self.frozen_start is None:
                        self.frozen_start = now
                    elif now - self.frozen_start > 2.0:
                        self.state = CameraState.CAMERA_FROZEN
                else:
                    self.frozen_start = None
            self.prev_frame_gray = gray

            if self.state not in (CameraState.BLACK_SCREEN, CameraState.CAMERA_FROZEN):
                self.state = CameraState.STREAMING

            # Computer Vision Detection Pipeline
            processed_frame, telemetry = self.detector.process_frame(frame, now)

            # Risk Engine Evaluation
            risk_res = risk_engine.evaluate(telemetry, frame=processed_frame)

            # FPS Computation
            self.frame_count += 1
            elapsed = now - self.fps_start_time
            if elapsed >= 1.0:
                self.fps = round(self.frame_count / elapsed, 1)
                self.frame_count = 0
                self.fps_start_time = now

            # Determine Candidate Position Status
            face_detected = telemetry.get("face_detected", False)
            multi_face = telemetry.get("multiple_faces", False)
            head_turned = telemetry.get("head_turned", False)
            offscreen = telemetry.get("offscreen", False)

            if not face_detected:
                cand_status = "NO_FACE"
            elif multi_face:
                cand_status = "MULTIPLE_FACES"
            elif self.brightness < 30.0:
                cand_status = "POOR_LIGHTING"
            elif head_turned:
                cand_status = "FACE_PARTIALLY_VISIBLE"
            elif offscreen:
                cand_status = "OFFSCREEN"
            else:
                cand_status = "ONE_FACE"

            # Telemetry Payload
            camera_telemetry = {
                "camera_state": self.state,
                "camera_connected": self.cap is not None and self.cap.isOpened(),
                "camera_streaming": self.state == CameraState.STREAMING,
                "camera_busy": self.state == CameraState.CAMERA_BUSY,
                "black_screen": self.state == CameraState.BLACK_SCREEN,
                "frozen": self.state == CameraState.CAMERA_FROZEN,
                "brightness": round(self.brightness, 1),
                "camera_resolution": f"{settings.CAM_W}x{settings.CAM_H}",
                "candidate_status": cand_status,
                "fps": self.fps,
                "risk": risk_res["risk"],
                "severity": risk_res["severity"],
                "active_window": "Exam Browser"
            }
            telemetry.update(camera_telemetry)

            with app_state.state_lock:
                app_state.current_fps = self.fps
                app_state.telemetry_data.update(telemetry)
                app_state.latest_frame = processed_frame.copy()

            with self.lock:
                self.current_frame = processed_frame.copy()

            time.sleep(0.015)

    def _generate_status_card_frame(self, message: str, subtitle: str) -> np.ndarray:
        """Generates an elegant status card image when camera feed is unavailable."""
        h, w = settings.CAM_H, settings.CAM_W
        frame = np.full((h, w, 3), (24, 26, 28), dtype=np.uint8)

        # Card container box
        cv2.rectangle(frame, (w // 6, h // 4), (w * 5 // 6, h * 3 // 4), (32, 35, 38), -1)
        cv2.rectangle(frame, (w // 6, h // 4), (w * 5 // 6, h * 3 // 4), (216, 176, 117), 1)

        cv2.putText(frame, "VERIFYAI CAMERA DIAGNOSTIC", (w // 6 + 30, h // 4 + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (216, 176, 117), 2)
        cv2.putText(frame, message, (w // 6 + 30, h // 4 + 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, subtitle, (w // 6 + 30, h // 4 + 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        return frame

    def get_mjpeg_stream(self):
        while True:
            with self.lock:
                frame = self.current_frame.copy() if self.current_frame is not None else None

            if frame is None:
                if self.state == CameraState.CAMERA_BUSY:
                    frame = self._generate_status_card_frame("Camera Currently In Use", "Close Zoom, Teams, or OBS to connect.")
                elif self.state == CameraState.BLACK_SCREEN:
                    frame = self._generate_status_card_frame("Black Screen Detected", "Check camera lighting or reconnect device.")
                elif self.state == CameraState.CAMERA_FROZEN:
                    frame = self._generate_status_card_frame("Stream Frozen", "Attempting automatic camera recovery...")
                else:
                    frame = self._generate_status_card_frame("Waiting for Camera Connection", "Plug in your camera device or grant permission.")

            if frame is not None:
                ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.033)

webcam_service = WebcamService()
