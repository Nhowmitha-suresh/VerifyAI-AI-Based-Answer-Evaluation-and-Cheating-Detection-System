"""
Filesystem Helpers for Organising Snapshots, Reports, and Logs.
"""

import os
import datetime

def get_today_snapshot_dir(base_dir: str = "snapshots") -> str:
    """Return date-partitioned snapshot directory path: snapshots/YYYY-MM-DD/."""
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(base_dir, today_str)
    os.makedirs(path, exist_ok=True)
    return path

def generate_timestamp_filename(prefix: str = "snapshot", ext: str = "jpg") -> str:
    """Generate timestamped filename: prefix_YYYYMMDD_HHMMSS.ext."""
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    return f"{prefix}_{now_str}.{ext}"
