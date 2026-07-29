"""
Unit Tests for AI Proctoring Core Services & Risk Engine.
"""

import numpy as np
from backend.services.gaze_service import GazeService
from backend.services.risk_service import risk_engine
from backend.utils.math_utils import calculate_ear

def test_calculate_ear():
    # Mock eye landmarks (6 points)
    eye = np.array([[10, 10], [12, 15], [14, 15], [20, 10], [14, 5], [12, 5]])
    ear = calculate_ear(eye)
    assert isinstance(ear, float)
    assert ear > 0

def test_gaze_service_init():
    gaze = GazeService()
    assert gaze.calib_center == (0.5, 0.5)

def test_risk_engine_evaluation():
    risk_engine.reset()
    telemetry = {
        "phone_detected": True,
        "multiface": False,
        "face_detected": True,
        "offscreen": True
    }
    res = risk_engine.evaluate(telemetry)
    assert res["risk"] > 0
    assert "MOBILE PHONE DETECTED" in res["violations"]
