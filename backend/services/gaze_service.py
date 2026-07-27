"""
Gaze Analytics & Iris Direction Tracking Service.
Provides 5-Zone Gaze Estimation (CENTER, LOOKING_LEFT, LOOKING_RIGHT, LOOKING_UP, LOOKING_DOWN),
Rapid Scan Detection, and Eye Aspect Ratio (EAR) Blink Counter.
"""

import collections
import time
import numpy as np
from typing import Tuple, Dict, Any, List
from backend.core.settings import settings
from backend.utils.math_utils import normalized_iris_center, calculate_ear

LEFT_IRIS_IDX = [474, 475, 476, 477]
RIGHT_IRIS_IDX = [469, 470, 471, 472]
LEFT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]

class GazeService:
    def __init__(self, calib_center: Tuple[float, float] = (0.5, 0.5)):
        self.calib_center = calib_center
        self.ema_nx, self.ema_ny = calib_center
        self.glance_buf = collections.deque()
        self.gaze_history = collections.deque(maxlen=15)
        
        # Blink Counter state
        self.ear_closed_start: float = 0.0
        self.eyes_currently_closed: bool = False
        self.blink_count: int = 0
        self.last_ear: float = 0.30

    def calibrate(self, new_center: Tuple[float, float]):
        self.calib_center = new_center
        self.ema_nx, self.ema_ny = new_center

    def process(self, lm_px: np.ndarray, now: float) -> Dict[str, Any]:
        """
        Process MediaPipe pixel landmark coordinates.
        Returns gaze directions, offscreen flag, rapid scan flag, and EAR calculation.
        """
        try:
            Lpts = lm_px[LEFT_IRIS_IDX]
            Rpts = lm_px[RIGHT_IRIS_IDX]
            Lc = tuple(Lpts.mean(axis=0).astype(int))
            Rc = tuple(Rpts.mean(axis=0).astype(int))

            nxL, nyL = normalized_iris_center(Lpts)
            nxR, nyR = normalized_iris_center(Rpts)
            nx, ny = (nxL + nxR) / 2.0, (nyL + nyR) / 2.0

            # Exponential Moving Average (EMA) Smoothing
            self.ema_nx = 0.35 * nx + 0.65 * self.ema_nx
            self.ema_ny = 0.35 * ny + 0.65 * self.ema_ny

            dx = self.ema_nx - self.calib_center[0]
            dy = self.ema_ny - self.calib_center[1]

            # Rapid Gaze Scan Detection
            rapid_scan = False
            self.gaze_history.append((self.ema_nx, self.ema_ny))
            if len(self.gaze_history) >= 10:
                gaze_arr = np.array(self.gaze_history)
                velocity = np.sum(np.abs(np.diff(gaze_arr[:, 0])))
                if velocity > settings.RAPID_SCAN_VELOCITY:
                    rapid_scan = True

            # 5-Zone Direction Classification
            gaze_dir = "CENTER"
            looking_left, looking_right, looking_up, looking_down = False, False, False, False

            if rapid_scan:
                gaze_dir = "RAPID SCANNING"
            elif abs(dx) > settings.GLANCE_THRESHOLD or abs(dy) > settings.GLANCE_THRESHOLD:
                self.glance_buf.append(now)
                if dx < -settings.GLANCE_THRESHOLD:
                    gaze_dir = "LOOKING LEFT"
                    looking_left = True
                elif dx > settings.GLANCE_THRESHOLD:
                    gaze_dir = "LOOKING RIGHT"
                    looking_right = True
                elif dy < -settings.GLANCE_THRESHOLD:
                    gaze_dir = "LOOKING UP"
                    looking_up = True
                else:
                    gaze_dir = "LOOKING DOWN"
                    looking_down = True
            else:
                self.glance_buf.clear()

            offscreen = False
            if self.glance_buf and (now - self.glance_buf[0]) > settings.GLANCE_SUSTAIN:
                offscreen = True

            # EAR Blink & Eye Closure Calculation
            left_ear = calculate_ear(lm_px[LEFT_EYE_LANDMARKS])
            right_ear = calculate_ear(lm_px[RIGHT_EYE_LANDMARKS])
            avg_ear = (left_ear + right_ear) / 2.0
            self.last_ear = avg_ear

            eyes_closed = False
            if avg_ear < settings.EAR_CLOSED_THRESH:
                if not self.eyes_currently_closed:
                    self.eyes_currently_closed = True
                    self.ear_closed_start = now
                    self.blink_count += 1
                elif (now - self.ear_closed_start) > settings.EAR_CLOSED_SUSTAIN:
                    eyes_closed = True
            else:
                self.eyes_currently_closed = False

            return {
                "gaze_direction": gaze_dir,
                "looking_left": looking_left,
                "looking_right": looking_right,
                "looking_up": looking_up,
                "looking_down": looking_down,
                "offscreen": offscreen,
                "rapid_scan": rapid_scan,
                "dx": float(dx),
                "dy": float(dy),
                "ear": float(avg_ear),
                "eyes_closed": eyes_closed,
                "blink_count": self.blink_count,
                "Lc": Lc,
                "Rc": Rc
            }
        except Exception:
            return {
                "gaze_direction": "CENTER",
                "looking_left": False,
                "looking_right": False,
                "looking_up": False,
                "looking_down": False,
                "offscreen": False,
                "rapid_scan": False,
                "dx": 0.0,
                "dy": 0.0,
                "ear": 0.3,
                "eyes_closed": False,
                "blink_count": self.blink_count,
                "Lc": (0, 0),
                "Rc": (0, 0)
            }
