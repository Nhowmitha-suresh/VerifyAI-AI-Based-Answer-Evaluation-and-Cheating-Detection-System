"""
Camera Management Module - Auto-Discovery & Verification Routine.
"""

import cv2
import time
import threading
import numpy as np
from .config import CAMERA_INDEXES, VERIFICATION_WINDOW_SEC

class CameraManager:
    BACKENDS = [
        (cv2.CAP_DSHOW, "DirectShow (CAP_DSHOW)"),
        (cv2.CAP_MSMF, "Media Foundation (CAP_MSMF)"),
        (cv2.CAP_ANY, "Default (CAP_ANY)")
    ]

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.cap = None
        self.current_frame = None
        self.running = False
        self.is_synthetic = False
        self._thread = None
        self._lock = threading.Lock()
        
        self._auto_discover_camera()

    def _auto_discover_camera(self):
        """Test camera indexes 0-4 using DirectShow, MSMF, and CAP_ANY with frame verification."""
        print("[CAMERA DISCOVERY] Starting multi-backend webcam auto-discovery (Indexes 0..4)...")
        
        for idx in CAMERA_INDEXES:
            for backend, backend_name in self.BACKENDS:
                print(f"[CAMERA DISCOVERY] Testing Camera Index {idx} using {backend_name}...")
                try:
                    test_cap = cv2.VideoCapture(idx, backend)
                    if test_cap and test_cap.isOpened():
                        test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        ret, frame = test_cap.read()
                        if ret and frame is not None and frame.size > 0:
                            print(f"[CAMERA DISCOVERY SUCCESS] Verified Camera Index {idx} using {backend_name}! Frame size: {frame.shape[1]}x{frame.shape[0]}")
                            self._display_verification_preview(test_cap, idx, backend_name, frame)
                            self.cap = test_cap
                            return
                        test_cap.release()
                except Exception as e:
                    print(f"[CAMERA DISCOVERY WARN] Index {idx} / {backend_name} failed: {e}")
                    pass

        print("[CAMERA DISCOVERY ERROR] Every backend (DirectShow, MSMF, CAP_ANY) and index (0..4) failed.")
        print("[CAMERA WARN] Enabling synthetic camera feed fallback.")
        self.is_synthetic = True

    def _display_verification_preview(self, test_cap, idx, backend_name, initial_frame):
        """Display test verification frame in OpenCV window for 3 seconds before starting application."""
        win_title = "Camera Verification"
        start_t = time.time()
        
        try:
            cv2.namedWindow(win_title, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_title, 960, 540)
        except Exception:
            pass

        while time.time() - start_t < VERIFICATION_WINDOW_SEC:
            ret, frame = test_cap.read()
            if not ret or frame is None:
                frame = initial_frame.copy()
            
            remaining = max(0.0, VERIFICATION_WINDOW_SEC - (time.time() - start_t))
            h, w = frame.shape[:2]
            
            # Render verification badge overlay
            cv2.rectangle(frame, (20, 20), (w - 20, 90), (10, 15, 25), -1)
            cv2.rectangle(frame, (20, 20), (w - 20, 90), (0, 230, 255), 2)
            cv2.putText(frame, f"CAMERA VERIFIED: Index {idx} ({backend_name})", (35, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 120), 2)
            cv2.putText(frame, f"STARTING IN {remaining:.1f}s...", (35, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 220, 255), 1)

            try:
                cv2.imshow(win_title, frame)
                if cv2.waitKey(50) & 0xFF == 27:
                    break
            except Exception:
                break

        try:
            cv2.destroyWindow(win_title)
        except Exception:
            pass

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
