"""
3D Head Pose Estimation & Lap Glance Analytics Module.
"""

import cv2
import math
import collections
import numpy as np
from .config import HP_IDX, YAW_THRESHOLD, YAW_FULLTURN, PITCH_THRESHOLD, PITCH_LAP_GLANCE

MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye outer corner
    (225.0, 170.0, -135.0),      # Right eye outer corner
    (-150.0, -150.0, -125.0),    # Left mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float64)

class HeadPoseEstimator:
    def __init__(self):
        self.ema_yaw = 0.0
        self.ema_pitch = 0.0
        self.head_buf = collections.deque()

    def process(self, lm_px, img_w, img_h, now, gaze_dir="", dy=0.0):
        """
        Estimate 3D head pose and return dict:
        {"head_status": str, "headturn": bool, "fullturn": bool, "lap_glance": bool, "axis_pts": tuple}
        """
        try:
            image_points = np.array([tuple(lm_px[i]) for i in HP_IDX], dtype=np.float64)
            focal_length = img_w
            center = (img_w / 2.0, img_h / 2.0)
            camera_matrix = np.array([[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]], dtype=np.float64)
            dist = np.zeros((4, 1))

            ok, rvec, tvec = cv2.solvePnP(MODEL_POINTS, image_points, camera_matrix, dist, flags=cv2.SOLVEPNP_ITERATIVE)
            if not ok:
                return {"head_status": "NORMAL", "headturn": False, "fullturn": False, "lap_glance": False, "axis_pts": None}

            rmat, _ = cv2.Rodrigues(rvec)
            sy = math.sqrt(rmat[0, 0] * rmat[0, 0] + rmat[1, 0] * rmat[1, 0])
            x = math.degrees(math.atan2(rmat[2, 1], rmat[2, 2]))
            y = math.degrees(math.atan2(-rmat[2, 0], sy))
            z = math.degrees(math.atan2(rmat[1, 0], rmat[0, 0]))

            # EMA Smoothing
            self.ema_yaw = 0.35 * y + 0.65 * self.ema_yaw
            self.ema_pitch = 0.35 * x + 0.65 * self.ema_pitch

            # 3D Nose Axis Vector Projection
            nose_end_3d = np.array([(0.0, 0.0, 1000.0)], dtype=np.float64)
            nose_end_2d, _ = cv2.projectPoints(nose_end_3d, rvec, tvec, camera_matrix, dist)
            p1 = (int(image_points[0][0]), int(image_points[0][1]))
            p2 = (int(nose_end_2d[0][0][0]), int(nose_end_2d[0][0][1]))

            headturn, fullturn, lap_glance = False, False, False
            head_status = "NORMAL"

            if self.ema_pitch > PITCH_LAP_GLANCE and (gaze_dir == "LOOKING DOWN" or dy > 0.18):
                lap_glance = True
                head_status = "LAP GLANCE (PHONE?)"
            elif abs(self.ema_yaw) > YAW_THRESHOLD or abs(self.ema_pitch) > PITCH_THRESHOLD:
                self.head_buf.append(now)
                head_status = f"TURNED ({int(self.ema_yaw)}deg)"
            else:
                self.head_buf.clear()

            if self.head_buf and (now - self.head_buf[0]) > 0.8:
                headturn = True
            if abs(self.ema_yaw) > YAW_FULLTURN:
                fullturn = True
                head_status = "FULL TURN"

            return {
                "head_status": head_status,
                "headturn": headturn,
                "fullturn": fullturn,
                "lap_glance": lap_glance,
                "pitch": self.ema_pitch,
                "yaw": self.ema_yaw,
                "roll": z,
                "axis_pts": (p1, p2)
            }
        except Exception:
            return {"head_status": "NORMAL", "headturn": False, "fullturn": False, "lap_glance": False, "axis_pts": None}
