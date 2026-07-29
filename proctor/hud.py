"""
Futuristic Glassmorphic HUD Telemetry Overlay Renderer.
"""

import cv2
import datetime
from .config import ALARM_MEDIUM, ALARM_HIGH

def draw_hud_panel(img, x, y, w, h, bg_color=(15, 20, 30), alpha=0.65, border_color=(0, 255, 200)):
    """Render semi-transparent glassmorphic HUD panel container."""
    try:
        overlay = img.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), bg_color, -1)
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        cv2.rectangle(img, (x, y), (x + w, y + h), border_color, 1)
    except Exception:
        pass


def draw_hud_header(frame, fps, elapsed_sec, score, status_text, window_title):
    """Render top glassmorphic status header banner."""
    h, w = frame.shape[:2]
    draw_hud_panel(frame, 10, 10, w - 20, 60, bg_color=(10, 15, 25), alpha=0.75, border_color=(0, 230, 255))
    
    cv2.putText(frame, "VERIFYAI PROCTORING SYSTEM", (25, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(frame, f"Active Window: {window_title[:28]}", (25, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 200, 220), 1)
    
    if score >= ALARM_HIGH:
        badge_color = (0, 0, 255)
    elif score >= ALARM_MEDIUM:
        badge_color = (0, 165, 255)
    else:
        badge_color = (0, 255, 120)

    cv2.rectangle(frame, (480, 22), (660, 50), badge_color, -1)
    cv2.putText(frame, status_text, (490, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 2)

    timer_str = str(datetime.timedelta(seconds=int(elapsed_sec)))
    cv2.putText(frame, f"TIME: {timer_str}", (w - 340, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 220, 255), 1)
    cv2.putText(frame, f"FPS: {fps:.1f}", (w - 130, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 200), 1)


def draw_risk_gauge(frame, score):
    """Render dynamic risk index bar at bottom of frame."""
    h, w = frame.shape[:2]
    x, y, gw, gh = 20, h - 75, w - 40, 38
    draw_hud_panel(frame, x, y, gw, gh, bg_color=(10, 15, 25), alpha=0.85, border_color=(100, 100, 100))
    
    ratio = min(1.0, score / ALARM_HIGH)
    fill_w = int((gw - 10) * ratio)
    
    if ratio > 0.7:
        fill_color = (0, 0, 255)
    elif ratio > 0.4:
        fill_color = (0, 165, 255)
    else:
        fill_color = (0, 255, 100)

    if fill_w > 0:
        cv2.rectangle(frame, (x + 5, y + 5), (x + 5 + fill_w, y + gh - 5), fill_color, -1)

    cv2.putText(frame, f"RISK INDEX: {score:.1f} / {ALARM_HIGH:.0f}", (x + 20, y + 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def draw_telemetry_panel(frame, flags):
    """Render telemetry status list on left side."""
    h, w = frame.shape[:2]
    pw, ph = 340, 300
    px, py = 20, 80
    draw_hud_panel(frame, px, py, pw, ph, bg_color=(10, 15, 25), alpha=0.75, border_color=(0, 200, 255))
    
    cv2.putText(frame, "TELEMETRY MONITOR", (px + 15, py + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 255), 2)
    cv2.line(frame, (px + 15, py + 33), (px + pw - 15, py + 33), (0, 180, 220), 1)

    items = [
        ("Mobile Phone AI", flags.get("phone_status", "CLEAR"), flags.get("phone_detected", False)),
        ("Window Focus", flags.get("window_status", "FOCUSED"), flags.get("window_switched", False)),
        ("Gaze Direction", flags.get("gaze_status", "CENTER"), flags.get("offscreen", False) or flags.get("rapid_scan", False)),
        ("Head Orientation", flags.get("head_status", "NORMAL"), flags.get("headturn", False) or flags.get("lap_glance", False)),
        ("Face Count", flags.get("face_status", "1 Face"), flags.get("multiface", False) or flags.get("occlusion", False)),
        ("Hand/Gadget Proxy", flags.get("hand_status", "CLEAR"), flags.get("handnear", False)),
        ("Audio/Collusion", flags.get("audio_status", "QUIET"), flags.get("othervoice", False)),
        ("Drowsiness/Blink", flags.get("ear_status", "ACTIVE"), flags.get("eyes_closed", False)),
    ]

    iy = py + 56
    for label, val, is_alert in items:
        dot_color = (0, 0, 255) if is_alert else (0, 255, 120)
        cv2.circle(frame, (px + 22, iy - 4), 4, dot_color, -1)
        cv2.putText(frame, f"{label}:", (px + 35, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (220, 220, 220), 1)
        
        val_color = (0, 80, 255) if is_alert else (0, 255, 180)
        cv2.putText(frame, str(val), (px + 190, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.44, val_color, 2 if is_alert else 1)
        iy += 28


def draw_event_feed(frame, recent_logs):
    """Render live incident feed list on right side."""
    h, w = frame.shape[:2]
    pw, ph = 340, 300
    px, py = w - pw - 20, 80
    draw_hud_panel(frame, px, py, pw, ph, bg_color=(10, 15, 25), alpha=0.75, border_color=(0, 200, 255))
    
    cv2.putText(frame, "INCIDENT FEED", (px + 15, py + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 255), 2)
    cv2.line(frame, (px + 15, py + 33), (px + pw - 15, py + 33), (0, 180, 220), 1)

    iy = py + 56
    for log in list(recent_logs)[-7:]:
        time_str = datetime.datetime.fromtimestamp(log[0]).strftime("%H:%M:%S")
        label = log[2] or "violation"
        score = log[1]
        cv2.putText(frame, f"[{time_str}] {label.upper()}", (px + 15, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (100, 200, 255), 1)
        cv2.putText(frame, f"+{score}", (px + pw - 50, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (0, 0, 255), 2)
        iy += 28
