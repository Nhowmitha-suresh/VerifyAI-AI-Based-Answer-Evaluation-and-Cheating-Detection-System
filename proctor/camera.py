"""
Camera Management Module - Multi-Threaded Video Capture with Fallback.
"""

import cv2
import time
import threading
import numpy as np

class CameraManager:
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.cap = None
        self.current_frame = None
        self.running = False
        self.is_synthetic = False
        self._thread = None
        self._lock = threading.Lock()
        
        self._init_camera()

    def _init_camera(self):
        """Probe camera indices and backends to select first working capture device."""
        for idx in [0, 1, 2]:
            for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
                try:
                    test_cap = cv2.VideoCapture(idx, backend)
                    if test_cap and test_cap.isOpened():
                        test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        ret, frame = test_cap.read()
                        if ret and frame is not None and frame.size > 0:
                            self.cap = test_cap
                            print(f"[CAMERA] Successfully opened Camera Index {idx} using backend {backend}.")
                            return
                        test_cap.release()
                except Exception:
                    pass

        print("[CAMERA WARN] No hardware webcam available. Enabling synthetic frame generator fallback.")
        self.is_synthetic = True

    def start(self):
        """Start asynchronous background frame capture thread."""
        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self._lock:
                        self.current_frame = frame
                else:
                    time.sleep(0.01)
            else:
                # Synthetic frame generation
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                cv2.putText(frame, "SYNTHETIC CAMERA FEED (NO WEBCAM)", (self.width // 2 - 280, self.height // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
                with self._lock:
                    self.current_frame = frame
                time.sleep(0.03)

    def read(self):
        """Get latest captured frame."""
        with self._lock:
            if self.current_frame is not None:
                return True, self.current_frame.copy()
            return False, None

    def release(self):
        """Stop capture thread and release hardware resources."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
