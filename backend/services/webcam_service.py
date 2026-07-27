"""
Asynchronous Camera Management & MJPEG Video Streaming Service.
Handles webcam auto-discovery, frame processing loop, FPS computation,
and JPEG stream encoding for the web dashboard.
"""

import cv2
import time
import threading
import numpy as np
from typing import Generator, Optional

from backend.core.settings import settings
from backend.core.logger import logger
from backend.core.app_state import app_state
from backend.services.detector_service import MultiModalDetector
from backend.services.risk_service import risk_engine

class WebcamService:
    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.camera_index: int = 0
        self.is_running: bool = False
        self.worker_thread: Optional[threading.Thread] = None
        
        self.detector = MultiModalDetector()
        self.current_frame: Optional[np.ndarray] = None
        self.lock = threading.Lock()

        # FPS counter
        self.fps: float = 0.0
        self.frame_count: int = 0
        self.fps_start_time: float = time.time()

    def _discover_camera(self) -> bool:
        for idx in settings.CAMERA_INDEXES:
            logger.info(f"[CAMERA DISCOVERY] Testing Camera Index {idx}...")
            # Try DirectShow first on Windows, then default
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if cv2.os.name == 'nt' else cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAM_W)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAM_H)
                    self.cap = cap
                    self.camera_index = idx
                    logger.info(f"[CAMERA SUCCESS] Successfully opened camera index {idx}.")
                    return True
                cap.release()
        logger.error("[CAMERA ERROR] Could not open any system webcam.")
        return False

    def start(self):
        if self.is_running:
            return
        if self.cap is None or not self.cap.isOpened():
            if not self._discover_camera():
                logger.error("Failed to start camera service: No active camera.")
                return

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
        logger.info("WebcamService stopped cleanly.")

    def _capture_loop(self):
        while self.is_running:
            if app_state.session_paused:
                time.sleep(0.1)
                continue

            if self.cap is None or not self.cap.isOpened():
                logger.warning("Camera disconnected. Retrying connection...")
                time.sleep(1.0)
                self._discover_camera()
                continue

            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                time.sleep(0.03)
                continue

            now = time.time()
            
            # Run Computer Vision Detection Pipeline
            processed_frame, telemetry = self.detector.process_frame(frame, now)

            # Evaluate Risk Score & Log Incidents
            risk_res = risk_engine.evaluate(telemetry, frame=processed_frame)

            # FPS Calculation
            self.frame_count += 1
            elapsed = now - self.fps_start_time
            if elapsed >= 1.0:
                self.fps = round(self.frame_count / elapsed, 1)
                self.frame_count = 0
                self.fps_start_time = now

            # Update App State Telemetry
            telemetry.update({
                "fps": self.fps,
                "risk": risk_res["risk"],
                "severity": risk_res["severity"],
                "active_window": "Exam Browser"
            })
            
            with app_state.state_lock:
                app_state.current_fps = self.fps
                app_state.telemetry_data.update(telemetry)
                app_state.latest_frame = processed_frame.copy()

            with self.lock:
                self.current_frame = processed_frame.copy()

            time.sleep(0.015)  # Yield for ~30-60 FPS

    def get_mjpeg_stream(self):
        while True:
            with self.lock:
                frame = self.current_frame.copy() if self.current_frame is not None else None

            if frame is not None:
                ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.033)  # ~30 FPS stream

webcam_service = WebcamService()
