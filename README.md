# AI Proctoring & Cheat Detection System

An advanced, multi-modal AI Proctoring and Anti-Cheat Detection Suite built with Python, OpenCV, MediaPipe FaceMesh & Iris tracking, Web Audio API, and real-time Telemetry Analytics.

![System Type](https://img.shields.io/badge/System-AI%20Proctoring%20%26%20Anti--Cheat-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-green)
![Mobile Phone AI](https://img.shields.io/badge/Object%20Detection-Mobile%20Phone%20%26%20Gadgets-red)

---

## 🌟 Key Features

### 1. Direct AI Mobile Phone & Forbidden Object Detection
- **Mobile Phone AI Detector**: Real-time object detection using OpenCV DNN (MobileNet-SSD COCO) and geometric slab heuristics.
- **Visual Bounding Boxes**: Highlights detected mobile phones directly on the camera feed with confidence ratings (`CELL PHONE 92%`).
- **Critical Violation Trigger**: Instantly triggers high-risk audio alarms (+15 score points) and captures evidence snapshots to `snapshots/`.

### 2. Active Window & Shortcut Proctoring (System Level)
- **Active Window Tracker**: OS-level active window title tracking (flags when candidate switches focus away from exam to Browser, ChatGPT, Telegram, Discord, or Notepad).
- **Shortcut & Focus Violation**: Automatically logs `window_switch` violations when window focus changes.

### 3. Advanced Telemetry & Cheating Detection Suite
- **Futuristic Glassmorphic HUD**: Cyberpunk overlay showing System Status badge, Active Window Title, FPS counter, Session Timer, and Live Risk Index (0-100%).
- **5-Zone Gaze Tracking**: Precise iris center tracking (`CENTER`, `LOOKING LEFT`, `LOOKING RIGHT`, `LOOKING UP`, `LOOKING DOWN`).
- **Rapid Gaze Scan Detector**: Tracks eye directional velocity to catch rapid scanning across off-screen cheat sheets.
- **Head Down & Lap Glance Detector**: Detects head pitch down (>20 deg) combined with gaze looking down (looking at a phone hidden on lap).
- **Secondary Screen / Phone Glow Detector**: Analyzes facial luminance variations to detect secondary monitor reflections or phone backlight glows on candidate's face.
- **3D Head Pose Estimation**: Computes Pitch, Yaw, and Roll using `solvePnP` with 3D orientation axis projected on face.
- **Hand & Gadget Proxy Detection**: Tracks hand landmarks near face or ear regions.
- **Multi-Face & Occlusion Monitor**: Flags multiple persons or candidate absence.
- **Voice & Collusion Detection**: Correlates audio energy with candidate mouth opening to detect secondary speakers.
- **Drowsiness & Eyes Closed Monitor**: Tracks Eye Aspect Ratio (EAR) for prolonged eye closures.

### 4. Automatic Evidence & Audit Reporting
- **Automated Snapshots**: Saves timestamped frames into `snapshots/` folder upon mobile phone detection or high risk scores.
- **CSV Incident Logging**: Logs all timestamped events to `proctor_log.csv`.
- **Interactive HTML Audit Report**: Automatically compiles an audit report (`proctor_report.html`) complete with violation statistics, timeline, and snapshot gallery upon exit.

---

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.9+
- Webcam & Microphone

### Installation
```bash
pip install -r requirements.txt
```

### Running the Python Engine
```bash
python eye_movement_cheat_alarm.py
```

### Running the Web Proctoring Dashboard
Open `face_landmarks_mediapipe.html` in Google Chrome or Microsoft Edge, or serve via HTTP:

```bash
python -m http.server 8000
```
Then open `http://localhost:8000/face_landmarks_mediapipe.html`.

---

## ⌨️ Interactive Keyboard Controls (Python App)

| Key | Action |
| --- | --- |
| `C` | Recalibrate gaze center baseline |
| `R` | Reset cumulative risk score to 0.0 |
| `S` | Manually capture an evidence snapshot |
| `Q` or `ESC` | Exit application and auto-generate `proctor_report.html` |
