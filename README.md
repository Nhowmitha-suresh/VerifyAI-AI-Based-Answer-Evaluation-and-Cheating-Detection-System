# VerifyAI - Modern AI Proctoring Web Platform 🚀

[![System Type](https://img.shields.io/badge/System-AI%20Proctoring%20%26%20Anti--Cheat-blue)](http://localhost:8000)
[![Framework](https://img.shields.io/badge/FastAPI-2.0.0-green)](https://fastapi.tiangolo.com)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--Time-purple)](http://localhost:8000/ws)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-Glassmorphism-38bdf8)](http://localhost:8000)

VerifyAI is an enterprise-grade, asynchronous AI Proctoring Web Application built with **FastAPI**, **MediaPipe**, **OpenCV**, **WebSockets**, and **Tailwind CSS**. 

It eliminates desktop GUI dependencies and provides real-time MJPEG webcam streaming, 5-zone gaze tracking, 3D head pose estimation, mobile phone AI detection, automated evidence snapshotting, and self-contained exam audit reports.

---

## 🌟 Key Features

1. **Modern Glassmorphic Web Dashboard**: Interactive Tailwind CSS UI featuring real-time risk progress gauges, Chart.js live risk graphs, status indicators, and live event timelines.
2. **Asynchronous MJPEG Video Stream (`/video_feed`)**: Zero OpenCV desktop popup windows. High-speed 30+ FPS video feed rendered directly in the browser via `<img src="/video_feed">`.
3. **High-Frequency WebSocket Telemetry (`/ws`)**: Streams real-time candidate telemetry packets every 100ms (risk score, 5-zone gaze direction, blinks, CPU/RAM stats, face status).
4. **Behavioral AI Risk Engine**: Calculates live cumulative risk score (0-100%) with exponential decay, severity levels (`NORMAL`, `WARNING`, `HIGH_RISK`, `CRITICAL`), and automated evidence snapshot triggers.
5. **Multi-Modal AI Detection**:
   - **MediaPipe Iris Tracking**: 5-Zone Gaze (`CENTER`, `LOOKING LEFT`, `LOOKING RIGHT`, `LOOKING UP`, `LOOKING DOWN`, `OFFSCREEN GAZE`, `RAPID SCANNING`).
   - **3D Head Pose `solvePnP`**: Computes Pitch, Yaw, and Roll with 3D nose orientation projection.
   - **OpenCV MobileNet-SSD Object Detector**: Detects mobile phones and prohibited gadgets.
   - **EAR Drowsiness & Blink Tracking**: Tracks Eye Aspect Ratio for blink counting and prolonged eyes-closed detection.
6. **Automated Reports & Snapshots**: Saves date-partitioned snapshots under `snapshots/YYYY-MM-DD/` and exports self-contained HTML audit reports into `reports/proctor_report.html`.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch FastAPI Server
```bash
uvicorn backend.main:app --reload
```

### 3. Open Browser Dashboard
Navigate to [http://localhost:8000](http://localhost:8000) in Google Chrome or Microsoft Edge.

---

## 📡 API Endpoints Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` or `/dashboard` | Glassmorphic Web Dashboard UI |
| `GET` | `/video_feed` | Live MJPEG Video Stream |
| `GET` | `/status` | Exam session status & system health |
| `GET` | `/health` | Health check endpoint |
| `GET` | `/risk` | Current risk score & severity |
| `GET` | `/events` | Logged incident timeline events |
| `GET` | `/snapshots` | Evidence snapshot gallery list |
| `GET` | `/report` | HTML exam audit report |
| `POST` | `/start` | Start proctoring session |
| `POST` | `/pause` | Pause proctoring session |
| `POST` | `/resume` | Resume proctoring session |
| `POST` | `/stop` | Stop session & generate HTML report |
| `POST` | `/snapshot` | Capture manual evidence snapshot |
| `POST` | `/recalibrate` | Recalibrate gaze baseline to center |
| `POST` | `/reset-risk` | Reset cumulative risk score to 0.0 |
| `WS` | `/ws` | WebSockets telemetry broadcast (~100ms) |

---

## 🐳 Docker Deployment

Run with Docker Compose:
```bash
docker-compose up --build
```
Open [http://localhost:8000](http://localhost:8000).
