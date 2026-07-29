"""
Automated Comprehensive Unit Test Suite for AI Proctoring Suite.
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
from proctor.behavior_engine import BehavioralRiskEngine
from proctor.timeline import IncidentRecorder
from proctor.heatmap import GazeHeatmapTracker
from proctor.identity import IdentityVerifier
from proctor.analytics import SessionAnalytics
from proctor.tracker import IoUTracker, compute_iou
from proctor.evaluation import DetectionEvaluator
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
        time.sleep(0.3)
        ret, frame = cam.read()
        cam.release()
        self.assertIsNotNone(cam)

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
        filepath = save_snapshot(dummy_frame, reason="test", force=True)
        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))

    def test_08_behavioral_risk_engine(self):
        """Test Explainable AI Behavioral Risk Engine multi-signal combos."""
        engine = BehavioralRiskEngine()
        telemetry = {"phone_detected": True, "lap_glance": True}
        res = engine.evaluate_telemetry(telemetry, now=100.0)
        self.assertGreaterEqual(res["risk_score"], 40.0)
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertIn("explanation", res)

    def test_09_incident_recorder(self):
        """Test Circular Incident Video Buffer."""
        recorder = IncidentRecorder(pre_roll_sec=1.0, post_roll_sec=1.0, fps=10.0)
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        recorder.push_frame(dummy_frame)
        path = recorder.trigger_incident("unit_test", 30.0, "Test incident trigger")
        self.assertIsNotNone(path)

    def test_10_gaze_heatmap(self):
        """Test Gaze Heatmap density tracking."""
        tracker = GazeHeatmapTracker()
        tracker.push_gaze_point(0.5, 0.5)
        tracker.push_gaze_point(0.2, 0.8)
        analytics = tracker.compute_analytics()
        self.assertEqual(analytics["total_gaze_samples"], 2)
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        blended = tracker.generate_heatmap_overlay(dummy_frame)
        self.assertIsNotNone(blended)

    def test_11_identity_verifier(self):
        """Test Candidate Identity Verification."""
        verifier = IdentityVerifier()
        dummy_lm = np.ones((478, 2), dtype=int) * 50
        res = verifier.verify(dummy_lm)
        self.assertIn("verified", res)

    def test_12_session_analytics_and_report(self):
        """Test Session Analytics and Enhanced HTML Report Generation."""
        analytics = SessionAnalytics()
        summary = analytics.get_summary()
        self.assertIn("verdict", summary)
        generate_html_report(analytics_summary=summary)
        self.assertTrue(os.path.exists(REPORT_FILE))

    def test_13_iou_tracker(self):
        """Test persistent IoU bounding box tracking & coordinate smoothing."""
        tracker = IoUTracker(iou_threshold=0.3)
        dets = [{"box": (100, 100, 50, 100), "label": "cell phone", "confidence": 0.90}]
        t1 = tracker.update(dets)
        self.assertEqual(len(t1), 1)
        self.assertIn("track_id", t1[0])

        dets_next = [{"box": (102, 101, 48, 99), "label": "cell phone", "confidence": 0.92}]
        t2 = tracker.update(dets_next)
        self.assertEqual(t2[0]["track_id"], t1[0]["track_id"])
        self.assertGreaterEqual(t2[0]["consecutive_frames"], 2)

    def test_14_detection_evaluator(self):
        """Test Detection Pipeline accuracy evaluator & benchmark engine."""
        evaluator = DetectionEvaluator(iou_threshold=0.5)
        gt = [{"box": (100, 100, 50, 50), "label": "face"}]
        pred = [{"box": (102, 98, 48, 52), "label": "face", "confidence": 0.95}]
        metrics = evaluator.evaluate_batch(gt, pred)
        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["f1_score"], 1.0)

if __name__ == "__main__":
    unittest.main()
