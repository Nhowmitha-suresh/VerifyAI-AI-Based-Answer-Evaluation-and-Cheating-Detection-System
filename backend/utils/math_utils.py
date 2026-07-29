"""
Mathematical & Geometric Utilities for Vision Analytics.
"""

import math
import numpy as np
from typing import Tuple, List

def calculate_ear(eye_landmarks: np.ndarray) -> float:
    """
    Calculate Eye Aspect Ratio (EAR) for blink & drowsiness detection.
    eye_landmarks: Array of 6 landmark points [(x, y), ...]
    """
    if len(eye_landmarks) < 6:
        return 0.3
    # Vertical distances
    A = np.linalg.norm(eye_landmarks[1] - eye_landmarks[5])
    B = np.linalg.norm(eye_landmarks[2] - eye_landmarks[4])
    # Horizontal distance
    C = np.linalg.norm(eye_landmarks[0] - eye_landmarks[3])
    if C == 0:
        return 0.3
    ear = (A + B) / (2.0 * C)
    return float(ear)

def normalized_iris_center(iris_points: np.ndarray) -> Tuple[float, float]:
    """
    Compute mean normalized center (x, y) of 4 iris landmark coordinates.
    """
    mean_pt = iris_points.mean(axis=0)
    return float(mean_pt[0]), float(mean_pt[1])

def calculate_distance(pt1: Tuple[float, float], pt2: Tuple[float, float]) -> float:
    """Euclidean distance between 2D points."""
    return math.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)
