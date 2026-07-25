"""
Incident Timeline & Circular Video Buffer Evidence Recording Engine.
Records 10 seconds before and 10 seconds after high-risk violation events into .mp4 clips.
"""

import os
import cv2
import time
import threading
import collections
from typing import Dict, List, Any
from .config import SNAPSHOT_DIR
from .logger import logger

class IncidentRecorder:
    """
    Circular Video Buffer & Incident Clip Generator.
    Continuously buffers incoming video frames. Upon high-risk incident triggers,
    it exports a video file containing 10s pre-event + 10s post-event frames.
    """

    def __init__(self, pre_roll_sec: float = 8.0, post_roll_sec: float = 8.0, fps: float = 20.0):
        self.pre_roll_sec = pre_roll_sec
        self.post_roll_sec = post_roll_sec
        self.fps = fps
        self.max_buffer_len = int((pre_roll_sec + post_roll_sec + 5) * fps)
        
        self.frame_buffer = collections.deque(maxlen=self.max_buffer_len)
        self.recorded_incidents: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.active_triggers = []
        
        if not os.path.exists(SNAPSHOT_DIR):
            os.makedirs(SNAPSHOT_DIR)

    def push_frame(self, frame: cv2.Mat, timestamp: float = None):
        """Push frame into circular buffer."""
        if frame is None or frame.size == 0:
            return
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            self.frame_buffer.append((timestamp, frame.copy()))

    def trigger_incident(self, reason: str, score: float, explanation: str) -> str:
        """
        Trigger incident video recording.
        Spawns background worker thread to wait for post-roll frames and compile MP4 video file.
        """
        now = time.time()
        incident_id = f"incident_{time.strftime('%Y%m%d_%H%M%S')}_{len(self.recorded_incidents) + 1}"
        video_filename = os.path.join(SNAPSHOT_DIR, f"{incident_id}.mp4")

        # Snapshot current pre-roll buffer snapshot
        with self._lock:
            pre_frames = [f for t, f in self.frame_buffer if (now - t) <= self.pre_roll_sec]

        incident_info = {
            "id": incident_id,
            "timestamp": now,
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reason": reason,
            "score": score,
            "explanation": explanation,
            "video_path": video_filename,
            "relative_video_path": os.path.basename(video_filename),
            "status": "RECORDING"
        }
        self.recorded_incidents.append(incident_info)

        logger.info(f"[INCIDENT RECORDER] Triggered video evidence capture: {incident_id} ({reason})")

        # Worker thread for post-roll collection & video writing
        def _write_worker(pre_f, target_path, info_dict):
            try:
                time.sleep(self.post_roll_sec)
                with self._lock:
                    post_frames = [f for t, f in self.frame_buffer if (t >= now)]

                all_frames = pre_f + post_frames
                if not all_frames:
                    info_dict["status"] = "FAILED"
                    return

                h, w = all_frames[0].shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(target_path, fourcc, self.fps, (w, h))

                for f in all_frames:
                    out.write(f)
                out.release()

                info_dict["status"] = "COMPLETE"
                info_dict["frame_count"] = len(all_frames)
                logger.info(f"[INCIDENT RECORDER] Successfully saved video clip: {target_path} ({len(all_frames)} frames)")
            except Exception as e:
                logger.error(f"[INCIDENT RECORDER ERROR] Video saving failed: {e}")
                info_dict["status"] = "ERROR"

        threading.Thread(target=_write_worker, args=(pre_frames, video_filename, incident_info), daemon=True).start()
        return video_filename

    def get_incidents(self) -> List[Dict[str, Any]]:
        return self.recorded_incidents
