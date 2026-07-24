"""
Gaze Tracking & Iris Directional Analytics Module.
"""

import collections
import numpy as np
from .config import LEFT_IRIS_IDX, RIGHT_IRIS_IDX, GLANCE_THRESHOLD, GLANCE_SUSTAIN, RAPID_SCAN_VELOCITY
from .utils import normalized_iris_center

class GazeTracker:
    def __init__(self, calib_center=(0.5, 0.5)):
        self.calib_center = calib_center
        self.ema_nx, self.ema_ny = calib_center
        self.glance_buf = collections.deque()
        self.gaze_history = collections.deque(maxlen=15)

    def calibrate(self, new_center):
        self.calib_center = new_center
        self.ema_nx, self.ema_ny = new_center

    def process(self, lm_px, now):
        """
        Process iris landmarks and return dict:
        {"gaze_direction": str, "offscreen_flag": bool, "rapid_scan_flag": bool, "Lc": tuple, "Rc": tuple}
        """
        try:
            Lpts = lm_px[LEFT_IRIS_IDX]
            Rpts = lm_px[RIGHT_IRIS_IDX]
            Lc = tuple(Lpts.mean(axis=0).astype(int))
            Rc = tuple(Rpts.mean(axis=0).astype(int))
            
            nxL, nyL = normalized_iris_center(Lpts)
            nxR, nyR = normalized_iris_center(Rpts)
            nx, ny = (nxL + nxR) / 2.0, (nyL + nyR) / 2.0

            # EMA Smoothing
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
                if velocity > RAPID_SCAN_VELOCITY:
                    rapid_scan = True

            gaze_dir = "CENTER"
            if rapid_scan:
                gaze_dir = "RAPID SCANNING"
            elif abs(dx) > GLANCE_THRESHOLD or abs(dy) > GLANCE_THRESHOLD:
                self.glance_buf.append(now)
                if dx < -GLANCE_THRESHOLD: gaze_dir = "LOOKING LEFT"
                elif dx > GLANCE_THRESHOLD: gaze_dir = "LOOKING RIGHT"
                elif dy < -GLANCE_THRESHOLD: gaze_dir = "LOOKING UP"
                else: gaze_dir = "LOOKING DOWN"
            else:
                self.glance_buf.clear()

            offscreen = False
            if self.glance_buf and (now - self.glance_buf[0]) > GLANCE_SUSTAIN:
                offscreen = True

            return {
                "gaze_direction": gaze_dir,
                "offscreen": offscreen,
                "rapid_scan": rapid_scan,
                "dx": dx,
                "dy": dy,
                "Lc": Lc,
                "Rc": Rc
            }
        except Exception:
            return {
                "gaze_direction": "CENTER",
                "offscreen": False,
                "rapid_scan": False,
                "dx": 0.0,
                "dy": 0.0,
                "Lc": (0, 0),
                "Rc": (0, 0)
            }
