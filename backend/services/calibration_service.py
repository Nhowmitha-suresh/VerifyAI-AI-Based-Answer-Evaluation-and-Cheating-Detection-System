"""
Gaze Calibration & Alignment Service.
"""

from typing import Tuple
from backend.core.app_state import app_state
from backend.core.logger import logger

class CalibrationService:
    def __init__(self):
        self.calibrated_center: Tuple[float, float] = (0.5, 0.5)

    def set_calibration(self, center: Tuple[float, float] = (0.5, 0.5)):
        self.calibrated_center = center
        app_state.calibration_status = True
        logger.info(f"Gaze baseline calibrated to: {center}")

calibration_service = CalibrationService()
