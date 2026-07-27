"""
Image Processing & Visual Drawing Utilities.
Draws bounding boxes, gaze indicators, head pose axes, and HUD text cleanly onto video frames.
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional

def draw_text_with_bg(
    img: np.ndarray,
    text: str,
    pos: Tuple[int, int],
    font=cv2.FONT_HERSHEY_SIMPLEX,
    scale=0.6,
    text_color=(255, 255, 255),
    bg_color=(0, 0, 0),
    thickness=1,
    padding=4
):
    """Draw text with semi-transparent rounded rectangular background."""
    (t_w, t_h), baseline = cv2.getTextSize(text, font, scale, thickness)
    x, y = pos
    back_rect = (x - padding, y - t_h - padding, t_w + 2 * padding, t_h + baseline + 2 * padding)
    
    cv2.rectangle(
        img,
        (back_rect[0], back_rect[1]),
        (back_rect[0] + back_rect[2], back_rect[1] + back_rect[3]),
        bg_color,
        -1
    )
    cv2.putText(img, text, (x, y), font, scale, text_color, thickness, cv2.LINE_AA)

def draw_bounding_box(
    img: np.ndarray,
    box: Tuple[int, int, int, int],
    label: str,
    confidence: float,
    color: Tuple[int, int, int] = (0, 0, 255)
):
    """Draw styled object bounding box with confidence badge."""
    x, y, w, h = box
    cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
    badge_text = f"{label.upper()} {int(confidence * 100)}%"
    draw_text_with_bg(img, badge_text, (x, max(20, y - 8)), scale=0.55, text_color=(255, 255, 255), bg_color=color, thickness=2)

def draw_head_pose_axis(img: np.ndarray, axis_pts: Optional[Tuple[Tuple[int, int], Tuple[int, int]]]):
    """Draw 3D nose orientation direction vector onto facial landmark frame."""
    if axis_pts and len(axis_pts) == 2:
        p1, p2 = axis_pts
        cv2.arrowedLine(img, p1, p2, (0, 255, 255), 2, cv2.LINE_AA, tipLength=0.25)
