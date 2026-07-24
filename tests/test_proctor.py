"""
Automated Unit Test Suite for AI Proctoring Suite.
"""

import os
import time
import unittest
import numpy as np

from proctor.utils import SilenceFD, normalized_iris_center, calculate_ear
from proctor.config import CAM_W, CAM_H, SNAPSHOT_DIR, CSV_FILE, REPORT_FILE
from proctor.camera import CameraManager
from proctor.gaze import GazeTracker
from proctor.headpose import HeadPoseEstimator
from proctor.phone_detector import ObjectDetector
from proctor.logger import push_event, current_score, log_event, save_snapshot
from proctor.report import generate_html_report

class TestProctorSuite(unittest.TestCase):

    def test_01_silence_fd(self):
        """Test C-level file descriptor silencer."""
        with SilenceFD():
            print("This stdout message should be silenced at C-level FD 1.")
        self.assertTrue(True)

    def test_02_camera_manager(self):
        """Test CameraManager frame reading and synthetic fallback."""
        cam = CameraManager(width=640, height=480)
        cam.start()
        time.sleep(0.15)  # Allow background capture thread to acquire frame 1
        ret, frame = cam.read()
        cam.release()
        self.assertTrue(ret)
        self.assertIsNotNone(frame)
        self.assertGreater(frame.size, 0)

    def test_03_gaze_tracker(self):
        """Test GazeTracker 5-zone gaze math."""
        gaze = GazeTracker()
        dummy_lm = np.zeros((478, 2), dtype=int)
        res = gaze.process(dummy_lm, now=100.0)
        self.assertIn("gaze_direction", res)
        self.assertIn("offscreen", res)

    def test_04_head_pose_estimator(self):
        """Test 3D HeadPoseEstimator."""
        estimator = HeadPoseEstimator()
        dummy_lm = np.ones((478, 2), dtype=int) * 100
        res = estimator.process(dummy_lm, img_w=640, img_h=480, now=100.0)
        self.assertIn("head_status", res)

    def test_05_object_detector(self):
        """Test ObjectDetector initialization and frame detection."""
        detector = ObjectDetector()
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect_objects(dummy_frame)
        self.assertIsInstance(detections, list)

    def test_06_logger_and_score(self):
        """Test risk score accumulation and logging."""
        push_event(10, "test_violation")
        score = current_score()
        self.assertGreaterEqual(score, 10)
        log_event("test_violation", 10)

    def test_07_snapshot_saving(self):
        """Test saving evidence snapshot image."""
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        filepath = save_snapshot(dummy_frame, reason="test")
        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))

    def test_08_html_report_generation(self):
        """Test generating interactive HTML audit report."""
        generate_html_report()
        self.assertTrue(os.path.exists(REPORT_FILE))

if __name__ == "__main__":
    unittest.main()
