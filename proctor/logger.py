"""
Logging, Event Score Tracking & Evidence Snapshot Manager.
"""

import os
import csv
import cv2
import time
import logging
import datetime
import collections
from .config import EVENT_WINDOW, CSV_FILE, SNAPSHOT_DIR

# Structured Logging Setup
logger = logging.getLogger("AIProctor")
logger.setLevel(logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] [%(asctime)s] %(message)s", "%H:%M:%S"))
    logger.addHandler(ch)

events = collections.deque()
all_logged_events = []
snapshot_count = 0

if not os.path.exists(SNAPSHOT_DIR):
    os.makedirs(SNAPSHOT_DIR)

if not os.path.exists(CSV_FILE):
    try:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "datetime", "event_label", "score", "total_score"])
    except Exception as e:
        logger.error(f"Could not initialize CSV file: {e}")

def push_event(score, label=None):
    now = time.time()
    events.append((now, score, label))
    cutoff = now - EVENT_WINDOW
    while events and events[0][0] < cutoff:
        events.popleft()

def current_score():
    return sum(s for _, s, _ in events)

def log_event(label, score):
    now = time.time()
    dt_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tot = current_score()
    all_logged_events.append({"timestamp": now, "datetime": dt_str, "label": label, "score": score, "total": tot})
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([now, dt_str, label, score, tot])
    except Exception as e:
        logger.error(f"Error writing to CSV log: {e}")

def save_snapshot(frame, reason="violation"):
    global snapshot_count
    if frame is None or frame.size == 0:
        return None
    snapshot_count += 1
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(SNAPSHOT_DIR, f"snapshot_{timestamp}_{reason}_{snapshot_count}.jpg")
    try:
        cv2.imwrite(filename, frame)
        logger.info(f"Saved evidence snapshot: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}")
        return None
