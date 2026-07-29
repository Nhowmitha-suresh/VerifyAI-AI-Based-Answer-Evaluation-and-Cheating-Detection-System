"""
Snapshot Service for Saving Evidence & Manual Snapshots.
Organizes snapshots under snapshots/YYYY-MM-DD/timestamp_reason.jpg.
"""

import os
import cv2
import datetime
import numpy as np
from typing import Dict, Any, Optional
from backend.core.settings import settings
from backend.core.logger import logger
from backend.core.app_state import app_state
from backend.utils.filesystem import get_today_snapshot_dir, generate_timestamp_filename

class SnapshotService:
    @staticmethod
    def capture_snapshot(frame: np.ndarray, reason: str = "manual", force: bool = False) -> Optional[Dict[str, Any]]:
        if not getattr(settings, "ENABLE_SNAPSHOTS", False) and not force:
            return None
        if frame is None or frame.size == 0:
            return None

        try:
            today_dir = get_today_snapshot_dir(settings.SNAPSHOT_DIR)
            filename = generate_timestamp_filename(prefix=f"snapshot_{reason}", ext="jpg")
            filepath = os.path.join(today_dir, filename)

            cv2.imwrite(filepath, frame)
            
            # Format relative URL for frontend consumption
            rel_url = f"/snapshots/{os.path.basename(today_dir)}/{filename}"
            
            snapshot_record = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "reason": reason,
                "file_path": filepath,
                "url": rel_url
            }

            app_state.add_snapshot(snapshot_record)
            logger.info(f"Saved evidence snapshot: {filepath} ({reason})")
            return snapshot_record
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None

snapshot_service = SnapshotService()
