# VerifyAI - Enterprise AI Examination Proctoring Platform 🚀

[![System Type](https://img.shields.io/badge/System-AI%20Proctoring%20%26%20Behavioral%20Telemetry-8B6B4A)](http://localhost:8000)
[![Framework](https://img.shields.io/badge/FastAPI-2.0.0-5C8D4D)](https://fastapi.tiangolo.com)
[![Design Language](https://img.shields.io/badge/Design-Minimal%20Luxury%20SaaS-C7A15A)](http://localhost:8000)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--Time-5C8D4D)](http://localhost:8000/ws)

VerifyAI is an enterprise-grade, human-centered AI Examination Proctoring & Behavioral Telemetry Platform inspired by Apple, Notion, Stripe, and Arc Browser. Built with **FastAPI**, **OpenCV**, **MediaPipe**, **WebSockets**, and **Vanilla CSS/Tailwind**, it provides real-time MJPEG webcam streaming, 5-zone gaze tracking, 3D head pose estimation, mobile phone AI detection, automated evidence snapshotting, candidate identity verification, and self-contained exam audit reports.

---

## 🌟 Key Features

1. **Minimal Luxury SaaS Interface**:
   - Designed with a calm, trustworthy aesthetic using Cream (`#F8F6F2`), Pure White cards (`#FFFFFF`), Soft Brown (`#8B6B4A`), and Muted Gold (`#C7A15A`).
   - Supports Dual Themes (Light & Dark) with persisted user preferences.
   - Zero cyberpunk, neon, or bright warning clutter.

2. **Complete Candidate Onboarding Workflow**:
   - 7-Stage Flow: `Landing Page` → `Candidate Profile Entry` → `Permission Center` → `Camera Health Diagnostics` → `AI Calibration` → `Environment Check` → `Enterprise Live Dashboard`.

3. **Enterprise Camera Lifecycle State Machine**:
   - Explicit state transitions: `INITIALIZING`, `DISCOVERING_CAMERA`, `REQUESTING_PERMISSION`, `CONNECTING`, `CONNECTED`, `STREAMING`, `WAITING_FOR_CANDIDATE`, `AI_PROCESSING`.
   - Continuous diagnostic health checks for `BLACK_SCREEN` (brightness < 5.0), `CAMERA_FROZEN` (delta < 0.1), `CAMERA_BUSY` (process locking), `NO_CAMERA_FOUND`, and `PERMISSION_DENIED`.
   - Diagnostic error cards with actionable recovery steps instead of blank rectangles.

4. **3-Layer Camera Feed & 60 FPS HUD Overlay**:
   - Bottom Layer: HTML5 Video / MJPEG `/video_feed`.
   - Middle Layer: 60 FPS `requestAnimationFrame` Canvas Overlay with smooth Exponential Moving Average (EMA) bounding box tracking.
   - Top Layer: Real-time telemetry HUD displaying timestamp, resolution, FPS, latency, and status.

5. **AI Explainability & Bounded Risk Engine**:
   - Strictly bounds cumulative behavioral risk score between `0%` and `100%` across 5 danger tiers (`Safe`, `Low`, `Moderate`, `High`, `Critical`).
   - Itemized score breakdown detailing exact contributing factors (`Phone Detected: +30`, `Offscreen Gaze: +5`, `Multiple Faces: +25`).

6. **High-Frequency Telemetry & Incident Recording**:
   - Real-time WebSocket channel broadcasting candidate telemetry every 100ms.
   - Automatic date-partitioned evidence snapshotting (`snapshots/YYYY-MM-DD/`) and self-contained HTML session audit reports (`reports/proctor_report.html`).

---

## 🏛️ System Architecture

```
                               ┌────────────────────────────────────────┐
                               │        Candidate Browser Client        │
                               │  (Minimal Luxury SaaS Dashboard UI)    │
                               └───────────────────┬────────────────────┘
                                                   │
                                     HTTP / WebSocket Telemetry (100ms)
                                                   │
                               ┌───────────────────▼────────────────────┐
                               │           FastAPI Backend Server       │
                               │     (REST API & WebSocket Manager)     │
                               └─────────┬────────────────────┬─────────┘
                                         │                    │
                    ┌────────────────────▼─────┐        ┌─────▼────────────────────┐
                    │ Multi-Modal Vision Engine│        │ Behavioral Risk Engine   │
                    │  • MobileNet-SSD Caffe   │        │  • Bounded 0-100% Index  │
                    │  • MediaPipe Gaze & Pose │        │  • Explainability Engine │
                    └──────────────────────────┘        └──────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch FastAPI Web Application
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 3. Open Browser Dashboard
Navigate to **[http://localhost:8000](http://localhost:8000)** in Google Chrome or Microsoft Edge.

---

## 📡 API Endpoints Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` or `/dashboard` | Minimal Luxury Enterprise Dashboard UI |
| `GET` | `/video_feed` | Asynchronous MJPEG Video Stream |
| `GET` | `/status` | Exam session status & system health |
| `GET` | `/health` | Subsystem health check endpoint |
| `GET` | `/risk` | Current risk score & severity breakdown |
| `GET` | `/events` | Logged incident timeline events |
| `GET` | `/snapshots` | Evidence snapshot gallery list |
| `GET` | `/report` | HTML exam audit report export |
| `POST` | `/start` | Start proctoring session |
| `POST` | `/pause` | Pause proctoring session |
| `POST` | `/resume` | Resume proctoring session |
| `POST` | `/stop` | Stop session & export HTML audit report |
| `POST` | `/snapshot` | Capture manual evidence snapshot |
| `POST` | `/recalibrate` | Recalibrate gaze baseline to center |
| `POST` | `/reset-risk` | Reset cumulative risk score index |
| `WS` | `/ws` | High-frequency WebSocket telemetry stream (~100ms) |

---

## 🐳 Docker Deployment

Run with Docker Compose:
```bash
docker-compose up --build
```
Open **[http://localhost:8000](http://localhost:8000)**.

---

## 📄 License & Contributors

- **Author / Lead Engineer**: Nhowmitha Suresh
- **Repository**: [VerifyAI AI-Based Answer Evaluation and Cheating Detection System](https://github.com/Nhowmitha-suresh/VerifyAI-AI-Based-Answer-Evaluation-and-Cheating-Detection-System.git)
- **License**: MIT License
