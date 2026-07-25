"""
Candidate Identity Verification & Unknown Person / Candidate Replacement Monitor.
Extracts normalized facial landmark distance descriptors to detect candidate swapping or unverified persons.
"""

import numpy as np
from typing import Dict, Any, Optional
from .logger import logger


class IdentityVerifier:
    """
    Computes invariant 3D facial landmark ratio descriptors to establish
    candidate identity baseline and detect mid-exam candidate swapping or unknown persons.
    """

    def __init__(self, mismatch_threshold: float = 0.18):
        self.mismatch_threshold = mismatch_threshold
        self.baseline_descriptor: Optional[np.ndarray] = None
        self.is_registered = False

    def extract_descriptor(self, lm_px: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract normalized facial geometric ratio vector from 478 MediaPipe landmarks.
        Uses scale and rotation invariant inter-landmark distance ratios.
        """
        if lm_px is None or len(lm_px) < 468:
            return None
        try:
            # Key landmark indices: Nose tip (1), Chin (152), Left Eye (33), Right Eye (263), Left Mouth (61), Right Mouth (291)
            p_nose = lm_px[1]
            p_chin = lm_px[152]
            p_leye = lm_px[33]
            p_reye = lm_px[263]
            p_lmouth = lm_px[61]
            p_rmouth = lm_px[291]

            face_height = np.linalg.norm(p_nose - p_chin)
            face_width = np.linalg.norm(p_leye - p_reye)
            ref_scale = max(1.0, (face_height + face_width) / 2.0)

            d_eye = np.linalg.norm(p_leye - p_reye) / ref_scale
            d_nose_chin = np.linalg.norm(p_nose - p_chin) / ref_scale
            d_nose_leye = np.linalg.norm(p_nose - p_leye) / ref_scale
            d_nose_reye = np.linalg.norm(p_nose - p_reye) / ref_scale
            d_mouth = np.linalg.norm(p_lmouth - p_rmouth) / ref_scale

            return np.array([d_eye, d_nose_chin, d_nose_leye, d_nose_reye, d_mouth], dtype=np.float32)
        except Exception as e:
            logger.debug(f"Descriptor extraction error: {e}")
            return None

    def register_baseline(self, lm_px: np.ndarray) -> bool:
        """Register candidate baseline identity descriptor."""
        desc = self.extract_descriptor(lm_px)
        if desc is not None:
            self.baseline_descriptor = desc
            self.is_registered = True
            logger.info("[IDENTITY VERIFIER] Candidate facial descriptor registered successfully.")
            return True
        return False

    def verify(self, lm_px: np.ndarray) -> Dict[str, Any]:
        """
        Verify candidate frame against registered baseline descriptor.
        """
        if not self.is_registered or self.baseline_descriptor is None:
            self.register_baseline(lm_px)
            return {"verified": True, "distance": 0.0, "status": "REGISTERED"}

        curr_desc = self.extract_descriptor(lm_px)
        if curr_desc is None:
            return {"verified": True, "distance": 0.0, "status": "NO_FACE"}

        dist = float(np.linalg.norm(self.baseline_descriptor - curr_desc))
        verified = dist < self.mismatch_threshold
        status = "VERIFIED" if verified else "CANDIDATE_MISMATCH"

        return {
            "verified": verified,
            "distance": round(dist, 4),
            "status": status
        }
