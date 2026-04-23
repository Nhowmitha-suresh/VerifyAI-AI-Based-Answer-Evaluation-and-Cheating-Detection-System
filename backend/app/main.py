from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib
from pydantic import BaseModel
from app.nlp import score_answer
import cv2
import numpy as np
import os
import json
import re
from datetime import datetime

app = FastAPI(title="verifAI - Starter API")

# Allow local frontend dev servers to talk to the API
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# If a built frontend exists at frontend/react-app/dist, serve it at the root.
# Look for a built frontend in either the backend folder or the repository root
cwd = os.getcwd()
repo_root = os.path.abspath(os.path.join(cwd, '..'))
dist_candidates = [
    os.path.join(cwd, 'frontend', 'react-app', 'dist'),
    os.path.join(repo_root, 'frontend', 'react-app', 'dist'),
]
served = False
for dist_path in dist_candidates:
    if os.path.isdir(dist_path):
        # Serve built static assets under /static to avoid shadowing API routes
        app.mount("/static", StaticFiles(directory=dist_path, html=True), name="frontend")
        # Also serve index.html at the root
        index_file = os.path.join(dist_path, 'index.html')
        if os.path.isfile(index_file):
            @app.get("/")
            def root_index():
                return FileResponse(index_file)
        print(f"Serving static frontend from {dist_path}")
        served = True
        break

if not served:
    # Fallback: serve top-level frontend/index.html if present (check backend and repo root)
    index_candidates = [
        os.path.join(cwd, 'frontend', 'index.html'),
        os.path.join(repo_root, 'frontend', 'index.html'),
    ]
    for index_path in index_candidates:
        if os.path.isfile(index_path):
            @app.get("/")
            def root_index():
                return FileResponse(index_path)
            print(f"Serving frontend index from {index_path}")
            break

class QAPayload(BaseModel):
    question: str
    answer: str
    keywords: list = []

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/nlp/score")
def nlp_score(payload: QAPayload):
    score, details = score_answer(payload.question, payload.answer, payload.keywords)
    return {"score": score, "details": details}

@app.post("/detect-face")
async def detect_face(file: UploadFile = File(...)):
    content = await file.read()
    nparr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {"faces": 0, "error": "could not decode image"}
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    return {"faces": int(len(faces))}


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    frames = 0
    try:
        # Prepare face detector once
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        while True:
            # Expect binary frames (JPEG/PNG bytes) from the client
            data = await websocket.receive_bytes()
            frames += 1
            # decode image
            try:
                nparr = np.frombuffer(data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception:
                img = None
            alerts = []
            integrity = 100
            faces_count = 0
            if img is None:
                alerts.append('invalid_frame')
                integrity -= 50
            else:
                try:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                    faces_count = int(len(faces))
                    if faces_count == 0:
                        alerts.append('no_face_detected')
                        integrity -= 60
                    elif faces_count > 1:
                        alerts.append('multiple_faces')
                        integrity -= 40
                    # brightness check
                    mean_brightness = float(np.mean(gray))
                    if mean_brightness < 40:
                        alerts.append('low_light')
                        integrity -= 20
                except Exception as e:
                    alerts.append('detection_error')
                    integrity -= 30

            # clamp integrity
            integrity = max(0, min(100, integrity))
            # log occasionally
            if frames % 100 == 0:
                print(f"WS frames={frames} faces={faces_count} alerts={alerts} integrity={integrity}")
            # If critical alerts, save flagged frame to disk asynchronously (best-effort)
            if img is not None and ( 'multiple_faces' in alerts or 'no_face_detected' in alerts or 'low_light' in alerts ):
                try:
                    # save to flagged_frames directory
                    root = os.path.join(os.getcwd(), 'flagged_frames')
                    os.makedirs(root, exist_ok=True)
                    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')
                    fname = f'ws_flagged_{ts}.jpg'
                    cv2.imwrite(os.path.join(root, fname), img)
                except Exception:
                    pass

            # send back an alerts payload
            await websocket.send_json({"frame": frames, "alerts": alerts, "integrity": integrity, "faces": faces_count})
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
        return


@app.post('/flagged-frame')
async def flagged_frame(file: UploadFile = File(...), reasons: str = None, integrity: str = '0'):
    """Receive flagged frames (image) from frontend for logging / review."""
    root = os.path.join(os.getcwd(), 'flagged_frames')
    os.makedirs(root, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')
    filename = f'flagged_{ts}.jpg'
    fpath = os.path.join(root, filename)
    content = await file.read()
    with open(fpath, 'wb') as fh:
        fh.write(content)
    meta = {'file': filename, 'reasons': None, 'integrity': integrity}
    try:
        if reasons:
            meta['reasons'] = json.loads(reasons)
    except Exception:
        meta['reasons'] = reasons
    # write metadata
    with open(os.path.join(root, filename + '.json'), 'w', encoding='utf-8') as mh:
        json.dump(meta, mh)
    return {'status': 'ok', 'file': filename}


@app.post('/audio/transcribe')
async def audio_transcribe(file: UploadFile = File(...)):
    """Accept an audio file, save it, and attempt server-side transcription using `whisper` if installed.
    Returns: {transcript, language, model}
    """
    root = os.path.join(os.getcwd(), 'audio_uploads')
    os.makedirs(root, exist_ok=True)
    fname = f'audio_{datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")}.wav'
    fpath = os.path.join(root, fname)
    content = await file.read()
    with open(fpath, 'wb') as fh:
        fh.write(content)
    # Try to import whisper and transcribe; if unavailable, return file path for client-side ASR
    print(f"Received audio file for transcription: {fpath}")
    try:
        import whisper
        model = whisper.load_model('small')
        result = model.transcribe(fpath)
        transcript = result.get('text','')
        print(f"Whisper transcript: {transcript}")
        return {'status': 'ok', 'transcript': transcript, 'language': result.get('language',''), 'model': 'whisper-small'}
    except Exception as e:
        print(f"Whisper transcription failed or not available: {e}")
        return {'status': 'no-model', 'message': 'Whisper not available on server or error during transcription', 'error': str(e), 'path': fpath}


class AuthEvaluatePayload(BaseModel):
    transcript: str
    duration_seconds: float


@app.post('/auth/evaluate')
def auth_evaluate(payload: AuthEvaluatePayload):
    """Simple heuristic authenticity evaluation based on transcript and duration.
    Returns authenticity score (0-100) and details.
    Heuristics used (starter):
      - words per minute (ideal 120-160)
      - filler word ratio (um, uh, like, you know)
      - lexical variability (unique/total words)
    """
    text = (payload.transcript or "").strip()
    dur = max(0.001, float(payload.duration_seconds or 0.0))
    words = [w for w in re.findall(r"\w+", text.lower())]
    total = len(words)
    unique = len(set(words))
    wpm = (total / dur) * 60.0 if dur>0 else 0.0
    fillers = ['um','uh','like','you know','i mean','so','actually','basically']
    filler_count = sum(1 for w in words if w in fillers)
    filler_ratio = (filler_count / total) if total else 0.0

    # WPM score: ideal 120-160 => full points; outside reduces
    if wpm >= 120 and wpm <= 160:
        wpm_score = 1.0
    else:
        # penalize linearly up to 0.0 at extremes (<60 or >220)
        if wpm < 60:
            wpm_score = max(0.0, (wpm - 20) / 40)
        elif wpm > 220:
            wpm_score = max(0.0, 1 - ((wpm - 160) / 120))
        else:
            wpm_score = 0.8

    variability = (unique / total) if total else 0.0

    # Compose authenticity: start at 100, subtract penalties
    score = 100.0
    score -= filler_ratio * 50.0
    score -= (1.0 - wpm_score) * 30.0
    score -= (0.5 - variability) * 40.0 if variability < 0.5 else 0.0
    score = max(0.0, min(100.0, score))

    details = {
        'words': total,
        'wpm': round(wpm,1),
        'filler_count': filler_count,
        'filler_ratio': round(filler_ratio,3),
        'variability': round(variability,3)
    }
    return {'authenticity_score': round(score,2), 'details': details}
