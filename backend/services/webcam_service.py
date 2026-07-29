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
        self.use_synthetic: bool = False
        self.worker_thread: Optional[threading.Thread] = None
        
        self.detector = MultiModalDetector()
        self.current_frame: Optional[np.ndarray] = None
        self.lock = threading.Lock()

        # FPS counter
        self.fps: float = 0.0
        self.frame_count: int = 0
        self.fps_start_time: float = time.time()

    def _discover_camera(self) -> bool:
        backends = []
        import os
        if os.name == 'nt':
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]

        for idx in settings.CAMERA_INDEXES:
            for backend in backends:
                try:
                    logger.info(f"[CAMERA DISCOVERY] Testing Index {idx} with backend {backend}...")
                    cap = cv2.VideoCapture(idx, backend)
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAM_W)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAM_H)
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            self.cap = cap
                            self.camera_index = idx
                            self.use_synthetic = False
                            logger.info(f"[CAMERA SUCCESS] Successfully opened camera index {idx}.")
                            return True
                        cap.release()
                except Exception as e:
                    logger.debug(f"Camera open attempt failed: {e}")

        logger.warning("[CAMERA NOTICE] No hardware webcam available. Enabling synthetic proctoring test feed...")
        self.use_synthetic = True
        return True

    def _generate_synthetic_frame(self) -> np.ndarray:
        """Generates a synthetic proctoring candidate test frame if no hardware webcam is attached."""
        h, w = settings.CAM_H, settings.CAM_W
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        # Background gradient
        for y in range(h):
            r = int(15 + 20 * (y / h))
            g = int(20 + 30 * (y / h))
            b = int(35 + 40 * (y / h))
            frame[y, :] = (b, g, r)

        # Draw candidate silhouette / face shape
        center_x, center_y = w // 2, h // 2
        t = time.time()
        dx = int(math.sin(t * 1.5) * 15)
        dy = int(math.cos(t * 1.2) * 8)

        # Draw Face oval
        cv2.ellipse(frame, (center_x + dx, center_y + dy), (120, 160), 0, 0, 360, (180, 200, 220), -1)
        cv2.ellipse(frame, (center_x + dx, center_y + dy), (120, 160), 0, 0, 360, (100, 120, 140), 3)

        # Draw Eyes
        cv2.circle(frame, (center_x + dx - 45, center_y + dy - 25), 14, (255, 255, 255), -1)
        cv2.circle(frame, (center_x + dx + 45, center_y + dy - 25), 14, (255, 255, 255), -1)
        pupil_dx = int(math.sin(t * 2.0) * 5)
        cv2.circle(frame, (center_x + dx - 45 + pupil_dx, center_y + dy - 25), 6, (50, 40, 20), -1)
        cv2.circle(frame, (center_x + dx + 45 + pupil_dx, center_y + dy - 25), 6, (50, 40, 20), -1)

        # Draw Nose & Mouth
        cv2.line(frame, (center_x + dx, center_y + dy - 10), (center_x + dx - 5, center_y + dy + 15), (100, 120, 140), 2)
        cv2.ellipse(frame, (center_x + dx, center_y + dy + 45), (30, 12), 0, 0, 180, (80, 70, 150), 3)

        cv2.putText(frame, "SYNTHETIC PROCTORING TEST STREAM", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        return frame

    def start(self):
        if self.is_running:
            return
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
