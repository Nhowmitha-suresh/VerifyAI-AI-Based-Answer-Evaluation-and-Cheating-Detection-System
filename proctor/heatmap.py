"""
Eye Gaze Heatmap, Fixation Map & Attention Analytics Module.
Tracks candidate gaze coordinates, generates spatial density heatmaps, scanpaths, and attention metrics.
"""

import os
import cv2
import numpy as np
from typing import Dict, List, Any, Tuple
from .config import SNAPSHOT_DIR
from .logger import logger


class GazeHeatmapTracker:
    """
    Accumulates normalized gaze coordinates across exam session,
    computes spatial attention percentage, fixation centers, and exports
    Gaussian-smoothed color heatmaps.
    """

    def __init__(self, grid_w: int = 128, grid_h: int = 72):
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.points_accumulated: List[Tuple[float, float]] = []
        self.density_grid = np.zeros((grid_h, grid_w), dtype=np.float32)
        self.center_count = 0
        self.distraction_count = 0

    def push_gaze_point(self, nx: float, ny: float):
        """
        Record a normalized gaze point (nx, ny in [0.0, 1.0]).
        """
        # Clamp to [0, 1]
        nx_c = max(0.0, min(1.0, float(nx)))
        ny_c = max(0.0, min(1.0, float(ny)))
        self.points_accumulated.append((nx_c, ny_c))

        # Update density grid
        gx = int(nx_c * (self.grid_w - 1))
        gy = int(ny_c * (self.grid_h - 1))
        self.density_grid[gy, gx] += 1.0

        # Center attention criteria (around 0.35 - 0.65)
        if 0.30 <= nx_c <= 0.70 and 0.30 <= ny_c <= 0.70:
            self.center_count += 1
        else:
            self.distraction_count += 1

    def compute_analytics(self) -> Dict[str, Any]:
        """Compute summary gaze distribution metrics."""
        total = len(self.points_accumulated)
        if total == 0:
            return {
                "total_gaze_samples": 0,
                "attention_percentage": 100.0,
                "distraction_percentage": 0.0,
                "fixation_count": 0,
                "avg_deviation": 0.0
            }

        attn_pct = round((self.center_count / total) * 100.0, 1)
        dist_pct = round((self.distraction_count / total) * 100.0, 1)

        # Calculate average radial distance from calibrated center (0.5, 0.5)
        pts = np.array(self.points_accumulated)
        deviations = np.sqrt((pts[:, 0] - 0.5) ** 2 + (pts[:, 1] - 0.5) ** 2)
        avg_dev = round(float(np.mean(deviations)), 3)

        return {
            "total_gaze_samples": total,
            "attention_percentage": attn_pct,
            "distraction_percentage": dist_pct,
            "fixation_count": self._estimate_fixations(),
            "avg_deviation": avg_dev
        }

    def _estimate_fixations(self, max_samples: int = 500) -> int:
        """Estimate number of distinct fixation clusters."""
        if len(self.points_accumulated) < 10:
            return 1
        pts = np.array(self.points_accumulated[-max_samples:])
        # Simple spatial grid clustering count
        discrete_grid = set((int(p[0] * 10), int(p[1] * 10)) for p in pts)
        return len(discrete_grid)

    def generate_heatmap_overlay(self, bg_frame: np.ndarray, alpha: float = 0.55) -> np.ndarray:
        """
        Generate Gaussian smoothed color heatmap rendered over background frame.
        """
        if bg_frame is None or bg_frame.size == 0:
            bg_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        h, w = bg_frame.shape[:2]

        if np.max(self.density_grid) == 0:
            return bg_frame.copy()

        # Resize density grid to frame size
        grid_resized = cv2.resize(self.density_grid, (w, h), interpolation=cv2.INTER_CUBIC)
        
        # Apply Gaussian Blur smoothing
        kernel_size = int(max(w, h) * 0.05) | 1
        blurred = cv2.GaussianBlur(grid_resized, (kernel_size, kernel_size), 0)

        # Normalize to 0-255
        norm_map = cv2.normalize(blurred, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

        # Apply Jet / Turbo Colormap
        color_heatmap = cv2.applyColorMap(norm_map, cv2.COLORMAP_JET)

        # Blend with original frame
        blended = cv2.addWeighted(bg_frame, 1.0 - alpha, color_heatmap, alpha, 0)

        # Save latest heatmap image file
        heatmap_path = os.path.join(SNAPSHOT_DIR, "gaze_heatmap_latest.jpg")
        try:
            cv2.imwrite(heatmap_path, blended)
        except Exception as e:
            logger.error(f"Failed to save gaze heatmap: {e}")

        return blended
