from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib
from pydantic import BaseModel
import logging
import asyncio
from app.nlp import score_answer
from app import nlp as nlp_tools
import cv2
import numpy as np
import os
import json
import re
from datetime import datetime
import io
import zipfile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Query
from uuid import uuid4
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False
try:
    import PyPDF2
    PDF_PYPDF2_AVAILABLE = True
except Exception:
    PDF_PYPDF2_AVAILABLE = False

app = FastAPI(title="verifAI - Starter API")

# basic logging
logger = logging.getLogger("verifiX")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# WebSocket processing lock (per-server default, individual connections will use their own lock)
ws_processing_lock = asyncio.Lock()

# Simple in-memory session store (for demo; replace with persistent store in prod)
_sessions = {}
# In-memory stores for uploaded resumes and generated reports (demo only)
_uploads = {}
_reports = {}


@app.post('/session/start')
def session_start():
    sid = uuid4().hex
    _sessions[sid] = {'created': datetime.utcnow().isoformat(), 'alerts': [], 'last_seen': None, 'processing': False}
    logger.info(f"session started {sid}")
    return {'session_id': sid}


@app.post('/session/end')
def session_end(sid: str = Query(None)):
    if sid and sid in _sessions:
        _sessions.pop(sid, None)
        logger.info(f"session ended {sid}")
    return {'status': 'ok'}

# Allow local frontend dev servers to talk to the API
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5176",
    "http://127.0.0.1:5176",
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
    try:
        score, details = score_answer(payload.question, payload.answer, payload.keywords)
        return {"score": score, "details": details}
    except Exception as e:
        logger.exception('nlp_score error')
        return JSONResponse(status_code=500, content={"error": "nlp scoring failed", "detail": str(e)})


@app.post('/evaluate')
def evaluate(payload: QAPayload):
    """Evaluate a single question/answer pair and return structured JSON with scores (0-10) and final average.
    """
    try:
        grammar = nlp_tools.grammar_score_text(payload.answer)
        relevance_pct, details = score_answer(payload.question, payload.answer, payload.keywords)
        # map 0-100 to 0-10
        relevance = int(round(relevance_pct / 10.0))
        genuineness = nlp_tools.genuineness_score_text(payload.answer)
        final = round((grammar + relevance + genuineness) / 3.0, 2)
        return {
            'question': payload.question,
            'answer': payload.answer,
            'grammar_score': int(grammar),
            'relevance_score': int(relevance),
            'genuineness_score': int(genuineness),
            'final_score': final,
            'nlp_details': details,
        }
    except Exception as e:
        logger.exception('evaluate error')
        return JSONResponse(status_code=500, content={'error':'evaluation failed','detail':str(e)})

@app.post("/detect-face")
async def detect_face(file: UploadFile = File(...)):
    try:
        content = await file.read()
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return JSONResponse(status_code=400, content={"faces": 0, "error": "could not decode image"})
        # downscale image for faster detection while preserving aspect
        h, w = img.shape[:2]
        max_dim = 800
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            img = cv2.resize(img, (int(w*scale), int(h*scale)))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        return {"faces": int(len(faces))}
    except Exception as e:
        logger.exception('detect_face error')
        return JSONResponse(status_code=500, content={"error": "face detection failed", "detail": str(e)})


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket, session: str = Query(None)):
    await websocket.accept()
    sid = session
    if not sid or sid not in _sessions:
        try:
            await websocket.send_json({'error': 'invalid_session'})
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
        return
    frames = 0
    # prepare detector once per connection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    conn_lock = asyncio.Lock()
    try:
        while True:
            # Expect binary frames (JPEG/PNG bytes) from the client
            try:
                data = await websocket.receive_bytes()
            except WebSocketDisconnect:
                logger.info('WebSocket client disconnected')
                return
            frames += 1
            alerts = []
            integrity = 100
            faces_count = 0

            # If another frame is still being processed, skip heavy processing to keep up
            if conn_lock.locked():
                # minimal response to keep client informed
                await websocket.send_json({"session": sid, "frame": frames, "alerts": ['processing_busy'], "integrity": integrity, "faces": faces_count})
                continue

            async with conn_lock:
                # decode and downscale for performance
                try:
                    nparr = np.frombuffer(data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                except Exception:
                    img = None

                if img is None:
                    alerts.append('invalid_frame')
                    integrity -= 50
                else:
                    try:
                        # downscale for detection speed
                        h, w = img.shape[:2]
                        max_dim = 800
                        if max(h, w) > max_dim:
                            scale = max_dim / float(max(h, w))
                            img = cv2.resize(img, (int(w*scale), int(h*scale)))
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
                        logger.exception('ws detection error')
                        alerts.append('detection_error')
                        integrity -= 30

                # clamp integrity
                integrity = max(0, min(100, integrity))
                # occasional log
                if frames % 100 == 0:
                    logger.info(f"WS frames={frames} faces={faces_count} alerts={alerts} integrity={integrity}")

                # If critical alerts, save flagged frame to disk asynchronously (best-effort)
                if img is not None and ( 'multiple_faces' in alerts or 'no_face_detected' in alerts or 'low_light' in alerts ):
                    try:
                        root = os.path.join(os.getcwd(), 'flagged_frames')
                        os.makedirs(root, exist_ok=True)
                        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')
                        fname = f'ws_flagged_{ts}.jpg'
                        cv2.imwrite(os.path.join(root, fname), img)
                    except Exception:
                        logger.exception('failed to save flagged frame')

                await websocket.send_json({"session": sid, "frame": frames, "alerts": alerts, "integrity": integrity, "faces": faces_count})
    except Exception:
        logger.exception('websocket_stream unexpected error')
        try:
            await websocket.close()
        except Exception:
            pass
        return


@app.post('/flagged-frame')
async def flagged_frame(file: UploadFile = File(...), reasons: str = None, integrity: str = '0', session: str = Query(None)):
    """Receive flagged frames (image) from frontend for logging / review."""
    root = os.path.join(os.getcwd(), 'flagged_frames')
    os.makedirs(root, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')
    filename = f'flagged_{ts}.jpg'
    fpath = os.path.join(root, filename)
    content = await file.read()
    try:
        with open(fpath, 'wb') as fh:
            fh.write(content)
    except Exception as e:
        logger.exception('failed to save flagged frame')
        return JSONResponse(status_code=500, content={'error':'failed to save file', 'detail': str(e)})
    meta = {'file': filename, 'reasons': None, 'integrity': integrity, 'session': session}
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
    logger.info(f"Received audio file for transcription: {fpath}")
    try:
        import whisper
        model = whisper.load_model('small')
        result = model.transcribe(fpath)
        transcript = result.get('text','')
        logger.info(f"Whisper transcript length={len(transcript)}")
        return {'status': 'ok', 'transcript': transcript, 'language': result.get('language',''), 'model': 'whisper-small'}
    except Exception as e:
        # Whisper not available or failed — return 503 so clients can handle gracefully
        logger.warning(f"Whisper transcription failed or not available: {e}")
        return JSONResponse(status_code=503, content={'status': 'no-model', 'message': 'Whisper not available on server or error during transcription', 'error': str(e), 'path': fpath})


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
    try:
        return {'authenticity_score': round(score,2), 'details': details}
    except Exception as e:
        logger.exception('auth_evaluate error')
        return JSONResponse(status_code=500, content={'error':'auth evaluation failed','detail':str(e)})


class GenerateQuestionsPayload(BaseModel):
    resume_text: str = ""


def _extract_resume_sections(text: str):
    """Attempt to extract Skills, Projects, Technologies, Coursework from free-form resume text.
    This uses simple header matching and fallback keyword extraction. It's intentionally conservative
    to avoid inventing facts when the resume is missing or ambiguous.
    Returns a dict with lists for each section.
    """
    sections = {'skills': [], 'projects': [], 'technologies': [], 'coursework': []}
    if not text or not text.strip():
        return sections
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cur_section = None
    for ln in lines:
        low = ln.lower()
        if low.startswith('skills') or low.startswith('skill:') or low == 'skills:':
            cur_section = 'skills'
            # strip header text
            rest = ln.split(':',1)[1].strip() if ':' in ln else ''
            if rest:
                sections['skills'] += [s.strip() for s in re.split('[,;|/]', rest) if s.strip()]
            continue
        if low.startswith('projects') or low.startswith('project:'):
            cur_section = 'projects'
            rest = ln.split(':',1)[1].strip() if ':' in ln else ''
            if rest:
                sections['projects'].append(rest)
            continue
        if low.startswith('technologies') or low.startswith('technology') or low.startswith('tech:'):
            cur_section = 'technologies'
            rest = ln.split(':',1)[1].strip() if ':' in ln else ''
            if rest:
                sections['technologies'] += [s.strip() for s in re.split('[,;|/]', rest) if s.strip()]
            continue
        if low.startswith('coursework') or low.startswith('courses'):
            cur_section = 'coursework'
            rest = ln.split(':',1)[1].strip() if ':' in ln else ''
            if rest:
                sections['coursework'] += [s.strip() for s in re.split('[,;|/]', rest) if s.strip()]
            continue

        # If current section is one of the known headers, append lines heuristically
        if cur_section == 'skills':
            sections['skills'] += [s.strip() for s in re.split('[,;|/]', ln) if s.strip()]
        elif cur_section == 'projects':
            sections['projects'].append(ln)
        elif cur_section == 'technologies':
            sections['technologies'] += [s.strip() for s in re.split('[,;|/]', ln) if s.strip()]
        elif cur_section == 'coursework':
            sections['coursework'] += [s.strip() for s in re.split('[,;|/]', ln) if s.strip()]

    # As a last resort, try to harvest some capitalized tokens as skills/technologies (conservative)
    if not sections['skills'] and not sections['technologies']:
        tokens = re.findall(r"\b[A-Z][A-Za-z0-9+#.+-]{1,20}\b", text)
        # filter common English words
        common = {'The','And','For','With','From','In','On','Or','To','By','Of'}
        tokens = [t for t in tokens if t not in common]
        sections['technologies'] = list(dict.fromkeys(tokens))[:10]

    return sections


def _extract_contact_meta(text: str):
    """Extract contact and metadata from resume text: emails, phones, education lines, domain, years_experience, name hints."""
    meta = {'emails': [], 'phones': [], 'education': [], 'domain': None, 'years_experience': None, 'name': None}
    if not text or not text.strip():
        return meta
    low = text.lower()
    # emails
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    meta['emails'] = list(dict.fromkeys(emails))
    # phones: crude but practical pattern
    phones = re.findall(r"\+?\d[\d\-\s\(\)]{7,}\d", text)
    meta['phones'] = list(dict.fromkeys([p.strip() for p in phones]))
    # education: prefer lines under Education header, otherwise lines containing University/College/Institute
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    edu = []
    cur = None
    for ln in lines:
        lowln = ln.lower()
        if lowln.startswith('education') or lowln.startswith('educational'):
            cur = 'edu'
            continue
        if cur == 'edu':
            if re.match(r'^[A-Z0-9]', ln):
                edu.append(ln)
            else:
                # stop if next header-like line
                if ':' in ln and len(ln.split())<6:
                    cur = None
        if any(k in lowln for k in ('university','college','institute','school')):
            edu.append(ln)
    # also search for degree keywords
    degs = re.findall(r"(b\.?s\.?|bachelor(?:'s)?|m\.?s\.?|master(?:'s)?|mba|ph\.?d\.?|doctorate)[^,\n]*", text, flags=re.I)
    for d in degs:
        edu.append(d.strip())
    meta['education'] = list(dict.fromkeys(edu))
    # years of experience
    m = re.search(r"(\d+)\s+years?\s+of\s+experience|(\d+)\+?\s+years", low)
    if m:
        yrs = next((g for g in m.groups() if g), None)
        try:
            meta['years_experience'] = int(yrs)
        except Exception:
            meta['years_experience'] = None
    # domain inference from keywords
    domain_map = {
        'Data Science': ['data science','machine learning','ml','deep learning','nlp','artificial intelligence','ai'],
        'Software Engineering': ['software engineer','backend','frontend','full stack','full-stack','developer','programming','software development'],
        'DevOps': ['devops','docker','kubernetes','ci/cd','infrastructure','terraform'],
        'Security': ['security','cyber','penetration','vulnerability'],
        'Finance': ['finance','financial','banking','trading','quant'],
        'Marketing': ['marketing','seo','content','social media'],
        'Embedded': ['embedded','firmware','microcontroller','rtos'],
        'Product': ['product manager','product management']
    }
    scores = {}
    for dom, keys in domain_map.items():
        for k in keys:
            if k in low:
                scores[dom] = scores.get(dom,0) + low.count(k)
    if scores:
        meta['domain'] = max(scores.items(), key=lambda x: x[1])[0]
    # name: look for explicit 'Name:' line or fallback later
    for ln in lines[:8]:
        if re.match(r'^(name[:\-\s])', ln.lower()):
            parts = ln.split(':',1)
            if len(parts)>1 and parts[1].strip():
                meta['name'] = parts[1].strip()
                break
    return meta


def _build_resume_questions(sections: dict, max_q: int = 5):
    """Generate up to `max_q` resume-focused questions based only on extracted sections.
    Avoids inventing any facts — if a section is empty it is skipped.
    """
    qlist = []
    if sections.get('projects'):
        for proj in sections['projects'][:2]:
            qlist.append({
                'question': f"Describe the architecture and key design decisions you made for the project: '{proj}'.",
                'difficulty': 'Medium',
                'expected_key_points': [
                    'High-level architecture (components, data flow)',
                    'Choices for protocols, storage, and scalability',
                    'Tradeoffs and lessons learned',
                ]
            })
    if sections.get('skills'):
        for skill in sections['skills'][:2]:
            qlist.append({
                'question': f"How have you applied the skill '{skill}' in a production or project setting? Provide concrete examples.",
                'difficulty': 'Medium',
                'expected_key_points': [
                    'Specific scenario or project where skill was used',
                    'Measured outcomes or improvements',
                    'Tools, libraries, or frameworks used',
                ]
            })
    if sections.get('technologies') and len(qlist) < max_q:
        for tech in sections['technologies'][:max(0, max_q - len(qlist))]:
            qlist.append({
                'question': f"Discuss trade-offs when using '{tech}' compared to alternatives for similar tasks.",
                'difficulty': 'Hard' if any(c.isupper() for c in tech) else 'Medium',
                'expected_key_points': [
                    'Strengths and limitations of the technology',
                    'Performance, scalability, and cost considerations',
                    'Relevant alternatives and comparison criteria',
                ]
            })
    if sections.get('coursework') and len(qlist) < max_q:
        for course in sections['coursework'][:max(0, max_q - len(qlist))]:
            qlist.append({
                'question': f"From your coursework '{course}', explain one concept you found most valuable and how you applied it.",
                'difficulty': 'Medium',
                'expected_key_points': [
                    'Clear explanation of the concept',
                    'Practical application or example',
                    'Limitations or extensions',
                ]
            })

    # Trim to max_q and return
    return qlist[:max_q]


def _cn_question_bank():
    # Deterministic list of Computer Networks questions (>=10)
    bank = [
        {'question': "Describe the seven layers of the OSI model and give one protocol or device example per layer.", 'difficulty': 'Medium',
         'expected_key_points': ['Names and order of layers', 'Examples (Ethernet, IP, TCP, HTTP)', 'Encapsulation concept']},
        {'question': "Map the OSI model to the TCP/IP model and explain practical reasons for the Internet's layering.", 'difficulty': 'Medium',
         'expected_key_points': ['Mapping (Application, Transport, Internet, Link)', 'Simplicity and adoption reasons']},
        {'question': "Explain the TCP three-way handshake and the role of sequence and acknowledgement numbers.", 'difficulty': 'Easy',
         'expected_key_points': ['SYN, SYN-ACK, ACK steps', 'ISN purpose', 'Teardown (FIN/ACK) and RST']},
        {'question': "Compare TCP congestion control phases: slow start, congestion avoidance, fast retransmit, and fast recovery.", 'difficulty': 'Hard',
         'expected_key_points': ['cwnd and ssthresh behavior', 'Exponential vs linear growth', 'Duplicate ACKs and fast retransmit']},
        {'question': "When would you choose UDP over TCP? Give three real-world use cases and explain app-level reliability strategies.", 'difficulty': 'Easy',
         'expected_key_points': ['Connectionless nature', 'Use cases: DNS, VoIP, gaming', 'Application-layer reliability (FEC, seq nums)']},
        {'question': "Walk through the DNS resolution process including iterative vs recursive queries and TTL implications.", 'difficulty': 'Medium',
         'expected_key_points': ['Resolver roles', 'Root/TLD/Authoritative servers', 'Caching and TTL']},
        {'question': "Explain HTTP/1.1 persistent connections vs HTTP/2 multiplexing and why HTTP/2 improves performance.", 'difficulty': 'Medium',
         'expected_key_points': ['Keep-alive, head-of-line blocking', 'HTTP/2 frames and multiplexing', 'TLS interactions']},
        {'question': "Describe NAT types (SNAT, DNAT, PAT) and how NAT impacts protocols embedding IP/port information.", 'difficulty': 'Medium',
         'expected_key_points': ['Source/Destination NAT definitions', 'Port mapping', 'NAT traversal (STUN/TURN)']},
        {'question': "Compare distance-vector and link-state routing protocols (e.g., RIP vs OSPF). Why does link-state often converge faster?", 'difficulty': 'Hard',
         'expected_key_points': ['Periodic updates vs LSDB flooding', 'SPF algorithm', 'Convergence and scaling tradeoffs']},
        {'question': "Explain BGP path selection basics and common mitigations for prefix hijacks.", 'difficulty': 'Hard',
         'expected_key_points': ['Local-pref, AS-PATH, MED, origin', 'RPKI and prefix filtering']},
        {'question': "Given a packet capture showing TCP retransmits and duplicate ACKs, how would you determine the root cause?", 'difficulty': 'Hard',
         'expected_key_points': ['Inspect seq/ack, RTT, window sizes', 'Use traceroute/mtr, check interface counters', 'Differentiate sender/receiver/network faults']},
        {'question': "A REST service across datacenters shows high tail latency—list network-level diagnostic steps you would take.", 'difficulty': 'Medium',
         'expected_key_points': ['Measure p95/p99 latency', 'Check packet loss, retransmits, MTU/PMTU', 'Load balancer and connection reuse checks']},
    ]
    return bank


def _os_question_bank():
    bank = [
        {'question': "Explain differences between a process and a thread and give an example where processes are preferred.", 'difficulty': 'Easy',
         'expected_key_points': ['Separate address spaces vs shared memory', 'IPC costs', 'Failure isolation']},
        {'question': "Describe the fork->exec model and how zombies and orphans are created and handled.", 'difficulty': 'Medium',
         'expected_key_points': ['fork duplicates, exec replaces', 'wait/waitpid to reap children', 'reparenting to init/systemd']},
        {'question': "Compare user-level threads and kernel-level threads and implications for blocking syscalls.", 'difficulty': 'Medium',
         'expected_key_points': ['User-level fast switches vs kernel scheduling', 'Blocking syscall behavior', 'M:N vs 1:1 models']},
        {'question': "Compare Round-Robin, SJF, Priority, and CFS scheduling in terms of fairness and starvation risk.", 'difficulty': 'Hard',
         'expected_key_points': ['Mechanics of each algorithm', 'Starvation and aging', 'CFS virtual runtime concept']},
        {'question': "List the four Coffman deadlock conditions and one practical prevention or recovery strategy.", 'difficulty': 'Hard',
         'expected_key_points': ['Mutual exclusion, hold-and-wait, no preemption, circular wait', 'Resource ordering or detection+recovery']},
        {'question': "Differentiate mutex, semaphore, and condition variable and give a use-case for each.", 'difficulty': 'Medium',
         'expected_key_points': ['Mutual exclusion, counting semaphores, cond-var wait/notify', 'Examples: critical section, resource pool, producer/consumer']},
        {'question': "Explain virtual memory translation with multi-level page tables and the role of the TLB.", 'difficulty': 'Hard',
         'expected_key_points': ['Page table walk, levels', 'TLB caching and miss cost', 'Large pages and TLB shootdown']},
        {'question': "Compare paging and segmentation; what fragmentation types do they suffer from?", 'difficulty': 'Medium',
         'expected_key_points': ['Paging eliminates external frag but has internal frag', 'Segmentation supports logical division and may have external frag']},
        {'question': "Describe the steps the OS takes on a page fault, including victim selection when no free frames exist.", 'difficulty': 'Medium',
         'expected_key_points': ['Trap to kernel, validate, load from swap/disk', 'Choose victim, writeback if dirty, update page tables']},
        {'question': "Explain common page replacement algorithms (LRU, Clock, FIFO) and how OS approximates LRU efficiently.", 'difficulty': 'Hard',
         'expected_key_points': ['LRU optimal but expensive, Clock as efficient approximation', 'Working set and thrashing']},
        {'question': "Describe kernel and user-space allocators (buddy, slab, malloc) and how they reduce fragmentation.", 'difficulty': 'Hard',
         'expected_key_points': ['Buddy coalescing, slab caches for small objects, malloc bins', 'Per-CPU caches and locking']},
        {'question': "A server is thrashing with high page fault rates—how would you diagnose and mitigate the issue?", 'difficulty': 'Hard',
         'expected_key_points': ['Collect vmstat/top, identify working set', 'Increase RAM, tune swappiness, find memory leaks']},
    ]
    return bank


def _hr_question_bank():
    # 50 standard HR questions (deterministic list)
    base = [
        "Tell me about yourself.",
        "Why are you interested in this role?",
        "What are your strengths?",
        "What are your weaknesses?",
        "Where do you see yourself in 5 years?",
        "Why did you leave your last job?",
        "Describe a difficult work situation and how you overcame it.",
        "How do you handle tight deadlines?",
        "Tell me about a time you failed and what you learned.",
        "How do you prioritize tasks?",
    ]
    # Expand to 50 by templating
    extras = []
    templates = [
        "Describe a time you led a team to success.",
        "How do you handle conflict with coworkers?",
        "What motivates you at work?",
        "Tell me about a project you are proud of.",
        "How do you handle constructive criticism?",
        "Explain a time you improved a process.",
        "What is your ideal work environment?",
        "How do you stay organized?",
        "What professional achievement are you most proud of?",
        "Describe how you adapt to change.",
    ]
    while len(extras) + len(base) < 50:
        extras.extend(templates)
    bank = [{'question': q, 'difficulty': 'Medium', 'expected_key_points': []} for q in (base + extras)[:50]]
    return bank


def _personality_question_bank():
    items = [
        "How would your colleagues describe you?",
        "What do you do to manage stress?",
        "Describe a hobby or interest outside work.",
        "How do you make decisions under uncertainty?",
        "Tell me about a recent book or article you enjoyed.",
        "What values are most important to you in a workplace?",
        "How do you approach teamwork?",
        "What are you passionate about?",
        "Describe a time you demonstrated resilience.",
        "How do you balance work and personal life?",
    ]
    return [{'question': q, 'difficulty': 'Easy', 'expected_key_points': []} for q in items]


def _render_pdf(payload: dict) -> bytes:
    """Render a clean PDF from the questions payload. Returns PDF bytes.
    Uses reportlab when available; otherwise raises RuntimeError.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError('reportlab not installed')
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    margin = 50
    y = height - margin
    line_height = 14

    def newline(n=1):
        nonlocal y
        y -= line_height * n
        if y < margin:
            c.showPage()
            y = height - margin

    # Title
    c.setFont('Helvetica-Bold', 16)
    c.drawString(margin, y, 'Interview Questions')
    newline(2)

    # Helper to render a section
    def render_section(title, items):
        nonlocal y
        c.setFont('Helvetica-Bold', 12)
        c.drawString(margin, y, title)
        newline(1)
        c.setFont('Helvetica', 10)
        for idx, it in enumerate(items, start=1):
            qtext = f"{idx}. {it.get('question','') }"
            # wrap long lines
            max_chars = 90
            parts = [qtext[i:i+max_chars] for i in range(0, len(qtext), max_chars)]
            for pidx, part in enumerate(parts):
                c.drawString(margin+10, y, part)
                newline(1)
            # difficulty
            diff = f"Difficulty: {it.get('difficulty','') }"
            c.drawString(margin+20, y, diff)
            newline(1)
            # expected key points as bullets
            ek = it.get('expected_key_points', []) or []
            for bullet in ek:
                # wrap bullet
                bparts = [bullet[i:i+80] for i in range(0, len(bullet), 80)]
                c.drawString(margin+30, y, u"\u2022 " + bparts[0])
                newline(1)
                for cont in bparts[1:]:
                    c.drawString(margin+40, y, cont)
                    newline(1)
            newline(1)

    # Resume section (if present)
    resume = payload.get('resume_questions', [])
    if resume:
        render_section('Resume-based Questions', resume)
    # CN
    render_section('Computer Networks', payload.get('computer_networks', []))
    # OS
    render_section('Operating Systems', payload.get('operating_systems', []))

    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


class ExportQuestionsPayload(BaseModel):
    resume_questions: list = []
    computer_networks: list = []
    operating_systems: list = []
    format: str = 'both'  # json, pdf, both


@app.post('/export-questions')
def export_questions(payload: ExportQuestionsPayload):
    """Export provided questions as downloadable JSON, PDF, or ZIP containing both.
    - `format` values: `json`, `pdf`, `both`.
    Returns a StreamingResponse or JSONResponse with appropriate `Content-Disposition` header.
    """
    # Normalize format
    fmt = (payload.format or 'both').lower()
    data = {
        'resume_questions': payload.resume_questions or [],
        'computer_networks': payload.computer_networks or [],
        'operating_systems': payload.operating_systems or [],
    }

    if fmt == 'json':
        content = json.dumps(data, indent=2, ensure_ascii=False)
        headers = { 'Content-Disposition': 'attachment; filename="questions.json"' }
        return JSONResponse(content=json.loads(content), headers=headers)

    # For PDF or both, attempt to build PDF
    if fmt in ('pdf','both'):
        try:
            pdf_bytes = _render_pdf(data)
        except Exception as e:
            # If PDF generation fails, fall back to returning JSON with error status
            return JSONResponse(status_code=500, content={'error': 'PDF generation failed', 'details': str(e)})

    if fmt == 'pdf':
        headers = { 'Content-Disposition': 'attachment; filename="questions.pdf"' }
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers=headers)

    # both -> build a zip archive with JSON and PDF
    if fmt == 'both':
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('questions.json', json.dumps(data, indent=2, ensure_ascii=False))
            zf.writestr('questions.pdf', pdf_bytes)
        buf.seek(0)
        headers = { 'Content-Disposition': 'attachment; filename="questions_bundle.zip"' }
        return StreamingResponse(buf, media_type='application/zip', headers=headers)

    return JSONResponse(status_code=400, content={'error': 'invalid format, must be json|pdf|both'})


@app.post('/generate-questions')
def generate_questions(payload: GenerateQuestionsPayload):
    """Generate interview questions in structured JSON.
    Behavior:
      - If `resume_text` is provided (non-empty), extract conservative resume facts and emit up to 5 resume-based questions.
      - Always emit at least 10 Computer Networks and 10 Operating Systems questions from deterministic banks.
    The endpoint avoids hallucination by only using extracted resume tokens and a fixed question bank.
    """
    res_text = (payload.resume_text or '').strip()
    sections = _extract_resume_sections(res_text)
    resume_qs = _build_resume_questions(sections) if res_text else []

    cn_bank = _cn_question_bank()
    os_bank = _os_question_bank()
    hr_bank = _hr_question_bank()
    personality_bank = _personality_question_bank()

    # Ensure at least 10 each
    cn_questions = cn_bank[:max(10, len(cn_bank))]
    os_questions = os_bank[:max(10, len(os_bank))]

    return {
        'resume_questions': resume_qs,
        'computer_networks': cn_questions,
        'operating_systems': os_questions,
        'hr_questions': hr_bank[:50],
        'personality_questions': personality_bank[:10],
    }


@app.post('/upload')
async def upload_resume(file: UploadFile = File(...)):
    """Accept a resume file, extract text (best-effort), and return parsed summary.
    Returns: { upload_id, name, skills, experience }
    """
    try:
        content = await file.read()
        text = ''
        # If PDF and PyPDF2 available, try extracting text from PDF bytes
        fname = (getattr(file, 'filename', '') or '').lower()
        if fname.endswith('.pdf') and PDF_PYPDF2_AVAILABLE:
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                pages = []
                for p in reader.pages:
                    try:
                        pages.append(p.extract_text() or '')
                    except Exception:
                        pages.append('')
                text = '\n'.join(pages)
            except Exception:
                text = ''
        else:
            # try decode as utf-8 text first, fallback to latin1
            try:
                text = content.decode('utf-8')
            except Exception:
                try:
                    text = content.decode('latin1')
                except Exception:
                    text = ''

        # very simple name extraction: first line with two capitalized words
        name = None
        for ln in (text or '').splitlines():
            ln = ln.strip()
            if not ln:
                continue
            parts = ln.split()
            if len(parts) >= 2 and all(p[0].isupper() for p in parts[:2] if p):
                name = ' '.join(parts[:2])
                break
        if not name:
            name = 'Candidate'

        sections = _extract_resume_sections(text or '')
        meta = _extract_contact_meta(text or '')
        upload_id = uuid4().hex
        _uploads[upload_id] = {'text': text or '', 'sections': sections, 'name': name, 'meta': meta, 'uploaded': datetime.utcnow().isoformat()}

        # derive experience stub from coursework or projects length
        experience = ''
        if sections.get('projects'):
            experience = sections['projects'][0]
        elif sections.get('coursework'):
            experience = ', '.join(sections['coursework'][:3])

        resp = {'upload_id': upload_id, 'name': name, 'skills': sections.get('skills',[]), 'experience': experience}
        # include contact meta in response (concise)
        resp['emails'] = meta.get('emails', [])
        resp['phones'] = meta.get('phones', [])
        resp['education'] = meta.get('education', [])
        resp['domain'] = meta.get('domain')
        resp['years_experience'] = meta.get('years_experience')
        return resp
    except Exception as e:
        logger.exception('upload_resume error')
        return JSONResponse(status_code=500, content={'error':'upload failed','detail': str(e)})


@app.get('/questions')
def get_questions(upload_id: str = Query(None)):
    """Return generated questions for an uploaded resume. If upload_id provided, use that resume; otherwise generate generic bank."""
    try:
        res_text = ''
        if upload_id and upload_id in _uploads:
            res_text = _uploads[upload_id].get('text','')

        sections = _extract_resume_sections(res_text)
        resume_qs = _build_resume_questions(sections) if res_text else []
        cn_bank = _cn_question_bank()
        os_bank = _os_question_bank()
        return {'resume_questions': resume_qs, 'computer_networks': cn_bank[:10], 'operating_systems': os_bank[:10]}
    except Exception as e:
        logger.exception('get_questions error')
        return JSONResponse(status_code=500, content={'error':'questions generation failed','detail':str(e)})


class SubmitPayload(BaseModel):
    upload_id: str
    answers: list


@app.post('/submit')
def submit_answers(payload: SubmitPayload):
    """Accept answers list and compute simple evaluation. Store a report for later GET /report."""
    try:
        upload_id = payload.upload_id
        answers = payload.answers or []
        total = len(answers)
        if total == 0:
            score = 0
        else:
            nonempty = sum(1 for a in answers if (a and str(a).strip()))
            score = int((nonempty/total)*100)

        integrity = 90 + (score//20) if score>0 else 50
        if integrity>100: integrity=100
        risk = 'Low' if score>=70 else ('Medium' if score>=40 else 'High')

        report = {'score': score, 'integrity': int(integrity), 'risk': risk, 'generated': datetime.utcnow().isoformat()}
        if upload_id:
            _reports[upload_id] = report

        return {'status':'ok','report': report}
    except Exception as e:
        logger.exception('submit_answers error')
        return JSONResponse(status_code=500, content={'error':'submit failed','detail':str(e)})


@app.get('/report')
def get_report(upload_id: str = Query(None)):
    try:
        if not upload_id or upload_id not in _reports:
            return JSONResponse(status_code=404, content={'error':'report not found'})
        return _reports[upload_id]
    except Exception as e:
        logger.exception('get_report error')
        return JSONResponse(status_code=500, content={'error':'failed','detail':str(e)})
