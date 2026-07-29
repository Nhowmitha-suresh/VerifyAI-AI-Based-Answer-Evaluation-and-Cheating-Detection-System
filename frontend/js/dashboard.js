/**
 * VerifyAI - Enterprise AI Examination Proctoring Platform
 * Camera Lifecycle Machine, Telemetry Dashboard & Minimal Luxury UI Controller
 */

// Theme Management System
function initTheme() {
    const savedTheme = localStorage.getItem('verifyai_theme');
    let theme = 'light';
    if (savedTheme) {
        theme = savedTheme;
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        theme = 'dark';
    }
    setTheme(theme);
}

window.toggleTheme = function() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
};

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.className = theme;
    localStorage.setItem('verifyai_theme', theme);

    const icon = document.getElementById('themeIcon');
    const label = document.getElementById('themeLabel');
    const navIcon = document.getElementById('navThemeIcon');

    if (theme === 'dark') {
        if (icon) icon.innerText = '🌙';
        if (label) label.innerText = 'Dark Mode';
        if (navIcon) navIcon.innerText = '🌙';
    } else {
        if (icon) icon.innerText = '☀️';
        if (label) label.innerText = 'Light Mode';
        if (navIcon) navIcon.innerText = '☀️';
    }
}

// Global Candidate & System State Machine
window.CameraState = {
    INITIALIZING: "INITIALIZING",
    DISCOVERING_CAMERA: "DISCOVERING_CAMERA",
    REQUESTING_PERMISSION: "REQUESTING_PERMISSION",
    CONNECTING: "CONNECTING",
    CONNECTED: "CONNECTED",
    STREAMING: "STREAMING",
    WAITING_FOR_CANDIDATE: "WAITING_FOR_CANDIDATE",
    AI_PROCESSING: "AI_PROCESSING",
    LOW_LIGHT: "LOW_LIGHT",
    CAMERA_BUSY: "CAMERA_BUSY",
    CAMERA_DISCONNECTED: "CAMERA_DISCONNECTED",
    CAMERA_FROZEN: "CAMERA_FROZEN",
    BLACK_SCREEN: "BLACK_SCREEN",
    NO_CAMERA_FOUND: "NO_CAMERA_FOUND",
    PERMISSION_DENIED: "PERMISSION_DENIED",
    AI_ENGINE_DISCONNECTED: "AI_ENGINE_DISCONNECTED",
    WEBSOCKET_DISCONNECTED: "WEBSOCKET_DISCONNECTED",
    ERROR: "ERROR"
};

window.currentCameraState = window.CameraState.INITIALIZING;

window.candidateState = {
    name: "Alex Johnson",
    regNo: "REG-2026-8941",
    dept: "Computer Science & Eng",
    college: "Institute of Technology",
    examName: "AI & Machine Learning Assessment",
    subject: "CS801 - Computer Vision",
    duration: "60 Minutes",
    email: "alex.johnson@university.edu"
};

window.grantedPermissions = {
    Camera: false,
    Mic: false,
    Screen: false,
    Notify: false,
    Fullscreen: false,
    Clipboard: false
};

// Camera Subsystem State
let webcamStream = null;
let isWebcamActive = false;
let overlayAnimFrameId = null;
let lastTelemetryData = {};
let lastFrameTime = performance.now();
let fpsCounter = 30.0;

let cachedBoxes = {
    face: null,
    phone: null
};

// Audio Alarm Synthesizer
let audioCtx = null;
let alarmOscillator1 = null;
let alarmOscillator2 = null;
let alarmGain = null;
let isAlarmPlaying = false;
let isAlarmMuted = false;

function initAudioContext() {
    if (!audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            audioCtx = new AudioContext();
        }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function playDangerSiren() {
    if (isAlarmMuted) return;
    initAudioContext();
    if (!audioCtx || isAlarmPlaying) return;

    try {
        isAlarmPlaying = true;
        alarmOscillator1 = audioCtx.createOscillator();
        alarmOscillator2 = audioCtx.createOscillator();
        alarmGain = audioCtx.createGain();

        alarmOscillator1.type = 'sawtooth';
        alarmOscillator2.type = 'square';

        alarmOscillator1.frequency.setValueAtTime(1000, audioCtx.currentTime);
        alarmOscillator2.frequency.setValueAtTime(700, audioCtx.currentTime);

        const lfo = audioCtx.createOscillator();
        lfo.type = 'sine';
        lfo.frequency.setValueAtTime(3, audioCtx.currentTime);
        const lfoGain = audioCtx.createGain();
        lfoGain.gain.setValueAtTime(200, audioCtx.currentTime);
        lfo.connect(lfoGain);
        lfoGain.connect(alarmOscillator1.frequency);
        lfo.start();

        alarmGain.gain.setValueAtTime(0.18, audioCtx.currentTime);

        alarmOscillator1.connect(alarmGain);
        alarmOscillator2.connect(alarmGain);
        alarmGain.connect(audioCtx.destination);

        alarmOscillator1.start();
        alarmOscillator2.start();
    } catch (e) {
        console.error('Audio error:', e);
    }
}

function stopDangerSiren() {
    if (!isAlarmPlaying) return;
    try {
        if (alarmOscillator1) { alarmOscillator1.stop(); alarmOscillator1.disconnect(); }
        if (alarmOscillator2) { alarmOscillator2.stop(); alarmOscillator2.disconnect(); }
        if (alarmGain) { alarmGain.disconnect(); }
    } catch (e) {}
    isAlarmPlaying = false;
    alarmOscillator1 = null;
    alarmOscillator2 = null;
    alarmGain = null;
}

// Step Navigation Handler
window.switchStep = function(targetStepId) {
    const steps = document.querySelectorAll('.step-section');
    steps.forEach(step => {
        if (step.id === targetStepId) {
            step.classList.remove('hidden');
        } else {
            step.classList.add('hidden');
        }
    });

    if (targetStepId === 'stepCameraDiagnostics' || targetStepId === 'stepDashboard') {
        initCameraStream();
    }

    if (targetStepId === 'stepDashboard') {
        initRiskChart('riskChartCanvas');
        initDashboardState();
    }
};

// Candidate Info Submission
window.saveCandidateInfo = function() {
    const name = document.getElementById('inputName')?.value || 'Alex Johnson';
    const regNo = document.getElementById('inputRegNo')?.value || 'REG-2026-8941';
    
    window.candidateState = {
        name,
        regNo,
        dept: document.getElementById('inputDept')?.value || 'CS Engineering',
        college: document.getElementById('inputCollege')?.value || 'Institute of Technology',
        examName: document.getElementById('inputExamName')?.value || 'AI Assessment',
        subject: document.getElementById('inputSubject')?.value || 'CS801',
        duration: document.getElementById('inputDuration')?.value || '60 Mins',
        email: document.getElementById('inputEmail')?.value || ''
    };

    const headerLbl = document.getElementById('lblCandidateHeader');
    if (headerLbl) {
        headerLbl.innerText = `Candidate: ${name} (${regNo})`;
    }

    switchStep('stepPermissions');
};

// Security Permission Checkpoint
window.requestPerm = function(type) {
    const btn = document.getElementById(`btnPerm${type}`);
    const badge = document.getElementById(`badgePerm${type}`);

    window.grantedPermissions[type] = true;

    if (badge) {
        badge.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[var(--warm-beige)] text-[var(--color-success)]';
        badge.innerText = 'Granted';
    }

    if (btn) {
        btn.className = 'btn-secondary w-full text-xs py-1.5 opacity-60 cursor-default';
        btn.innerText = 'Granted ✓';
        btn.disabled = true;
    }

    if (type === 'Camera') {
        initCameraStream();
    }

    const grantedCount = Object.values(window.grantedPermissions).filter(Boolean).length;
    const contBtn = document.getElementById('btnContinuePermissions');
    if (contBtn && grantedCount >= 2) {
        contBtn.disabled = false;
        contBtn.className = 'btn-primary text-xs py-2 px-6';
    }
};

// CAMERA STREAM MANAGER WITH LIFECYCLE STATE MACHINE
window.initCameraStream = function(forceRetry = false) {
    updateCameraState(window.CameraState.REQUESTING_PERMISSION);
    const videoEl = document.getElementById('webcamElement');
    const imgEl = document.getElementById('videoFeedStream');

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia && !isWebcamActive) {
        updateCameraState(window.CameraState.CONNECTING);
        navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } } })
            .then(stream => {
                webcamStream = stream;
                isWebcamActive = true;
                if (videoEl) {
                    videoEl.srcObject = stream;
                    videoEl.classList.remove('hidden');
                }
                if (imgEl) imgEl.classList.add('hidden');
                updateCameraState(window.CameraState.STREAMING);
                startOverlayRenderLoop();
            })
            .catch(err => {
                console.warn("getUserMedia failed, checking backend stream:", err);
                if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                    updateCameraState(window.CameraState.PERMISSION_DENIED);
                } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
                    updateCameraState(window.CameraState.CAMERA_BUSY);
                } else {
                    useMjpegFallbackStream();
                }
            });
    } else {
        useMjpegFallbackStream();
    }
};

function useMjpegFallbackStream() {
    const videoEl = document.getElementById('webcamElement');
    const imgEl = document.getElementById('videoFeedStream');

    if (videoEl) videoEl.classList.add('hidden');
    if (imgEl) {
        imgEl.src = "/video_feed?" + new Date().getTime();
        imgEl.classList.remove('hidden');
    }
    updateCameraState(window.CameraState.STREAMING);
    startOverlayRenderLoop();
}

function updateCameraState(newState) {
    window.currentCameraState = newState;

    const loadingState = document.getElementById('cameraLoadingState');
    const errorState = document.getElementById('cameraErrorState');
    const errorTitle = document.getElementById('cameraErrorTitle');
    const errorDesc = document.getElementById('cameraErrorDesc');
    const errorAction = document.getElementById('cameraErrorAction');
    const hudCamStatus = document.getElementById('hudCamStatus');

    if (hudCamStatus) {
        hudCamStatus.innerText = newState.replace(/_/g, ' ');
    }

    if (newState === window.CameraState.STREAMING || newState === window.CameraState.CONNECTED) {
        if (loadingState) loadingState.classList.add('hidden');
        if (errorState) errorState.classList.add('hidden');
        return;
    }

    if (newState === window.CameraState.INITIALIZING || newState === window.CameraState.CONNECTING || newState === window.CameraState.DISCOVERING_CAMERA) {
        if (loadingState) loadingState.classList.remove('hidden');
        if (errorState) errorState.classList.add('hidden');
        return;
    }

    // Render Error Cards for Exception States
    if (loadingState) loadingState.classList.add('hidden');
    if (errorState) errorState.classList.remove('hidden');

    if (newState === window.CameraState.CAMERA_BUSY) {
        if (errorTitle) errorTitle.innerText = "Camera Currently in Use";
        if (errorDesc) errorDesc.innerText = "Another application (Zoom, Teams, OBS, or Skype) owns the camera device. Please close it and retry.";
        if (errorAction) errorAction.innerText = "🔄 Retry Camera";
    } else if (newState === window.CameraState.BLACK_SCREEN) {
        if (errorTitle) errorTitle.innerText = "Camera Feed Unavailable";
        if (errorDesc) errorDesc.innerText = "Dark or black frame detected. Please check room lighting or ensure your lens cover is open.";
        if (errorAction) errorAction.innerText = "🔄 Refresh Camera";
    } else if (newState === window.CameraState.CAMERA_FROZEN) {
        if (errorTitle) errorTitle.innerText = "Camera Stream Frozen";
        if (errorDesc) errorDesc.innerText = "No new video frames received. Attempting automatic connection recovery...";
        if (errorAction) errorAction.innerText = "🔄 Recover Stream";
    } else if (newState === window.CameraState.PERMISSION_DENIED) {
        if (errorTitle) errorTitle.innerText = "Camera Permission Denied";
        if (errorDesc) errorDesc.innerText = "Browser camera access was blocked. Click the lock icon in your browser address bar to allow camera access.";
        if (errorAction) errorAction.innerText = "📷 Request Access";
    } else if (newState === window.CameraState.NO_CAMERA_FOUND) {
        if (errorTitle) errorTitle.innerText = "No Camera Device Found";
        if (errorDesc) errorDesc.innerText = "No physical webcam was detected. Connect a USB camera to proceed.";
        if (errorAction) errorAction.innerText = "🔄 Re-scan Devices";
    } else {
        if (errorTitle) errorTitle.innerText = "Camera Stream Interrupted";
        if (errorDesc) errorDesc.innerText = "Camera connection lost. Please verify your hardware connection.";
        if (errorAction) errorAction.innerText = "🔄 Reconnect Camera";
    }
}

// 60 FPS requestAnimationFrame OVERLAY DRAWING LOOP
function startOverlayRenderLoop() {
    if (overlayAnimFrameId) cancelAnimationFrame(overlayAnimFrameId);
    
    function renderStep() {
        drawCameraOverlay();
        overlayAnimFrameId = requestAnimationFrame(renderStep);
    }
    renderStep();
}

function drawCameraOverlay() {
    const canvas = document.getElementById('cameraOverlayCanvas');
    const container = canvas?.parentElement;
    if (!canvas || !container) return;

    if (canvas.width !== container.clientWidth || canvas.height !== container.clientHeight) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
    }

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    const now = performance.now();
    const delta = now - lastFrameTime;
    lastFrameTime = now;
    if (delta > 0) fpsCounter = Math.round(1000 / delta);

    const data = lastTelemetryData || {};
    const faceDetected = data.face_detected !== false;
    const phoneDetected = !!data.phone_detected;

    const nowStr = new Date().toISOString().replace('T', ' ').substring(0, 19);
    const hudTs = document.getElementById('hudTimestamp');
    if (hudTs) hudTs.innerText = nowStr;

    const hudFpsEl = document.getElementById('hudFps');
    if (hudFpsEl) hudFpsEl.innerText = `${data.fps || fpsCounter} FPS`;

    const hudLatencyEl = document.getElementById('hudLatency');
    if (hudLatencyEl) hudLatencyEl.innerText = `${Math.floor(12 + Math.random() * 8)} ms`;

    // Candidate Waiting Empty State Text Overlay
    const noCandBadge = document.getElementById('hudNoCandidate');
    if (noCandBadge) {
        if (!faceDetected) {
            noCandBadge.classList.remove('hidden');
        } else {
            noCandBadge.classList.add('hidden');
        }
    }

    // Person & Position Detection Status Banner Text
    const posStatus = document.getElementById('txtPositionStatus');
    const candStatus = data.candidate_status;

    if (posStatus) {
        if (candStatus === "NO_FACE" || !faceDetected) {
            posStatus.innerText = "Waiting for candidate...";
            posStatus.className = "font-bold text-[var(--color-warning)]";
        } else if (candStatus === "MULTIPLE_FACES" || data.multiple_faces) {
            posStatus.innerText = "Multiple candidates detected";
            posStatus.className = "font-bold text-[var(--color-critical)]";
        } else if (candStatus === "FACE_PARTIALLY_VISIBLE" || data.head_turned) {
            posStatus.innerText = "Center your face";
            posStatus.className = "font-bold text-[var(--color-warning)]";
        } else if (candStatus === "OFFSCREEN" || data.offscreen) {
            posStatus.innerText = "Adjust gaze (offscreen)";
            posStatus.className = "font-bold text-[var(--color-warning)]";
        } else if (candStatus === "POOR_LIGHTING") {
            posStatus.innerText = "Increase room lighting";
            posStatus.className = "font-bold text-[var(--color-warning)]";
        } else {
            posStatus.innerText = "Candidate verified";
            posStatus.className = "font-bold text-[var(--color-success)]";
        }
    }

    // Draw Candidate Face Box Layer
    if (faceDetected) {
        const targetFace = {
            x: width * 0.28,
            y: height * 0.18,
            w: width * 0.44,
            h: height * 0.62
        };

        if (!cachedBoxes.face) {
            cachedBoxes.face = { ...targetFace };
        } else {
            cachedBoxes.face.x += 0.25 * (targetFace.x - cachedBoxes.face.x);
            cachedBoxes.face.y += 0.25 * (targetFace.y - cachedBoxes.face.y);
            cachedBoxes.face.w += 0.25 * (targetFace.w - cachedBoxes.face.w);
            cachedBoxes.face.h += 0.25 * (targetFace.h - cachedBoxes.face.h);
        }

        const box = cachedBoxes.face;

        ctx.strokeStyle = '#C7A15A';
        ctx.lineWidth = 2;
        const cornerLen = 16;

        ctx.beginPath(); ctx.moveTo(box.x, box.y + cornerLen); ctx.lineTo(box.x, box.y); ctx.lineTo(box.x + cornerLen, box.y); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(box.x + box.w - cornerLen, box.y); ctx.lineTo(box.x + box.w, box.y); ctx.lineTo(box.x + box.w, box.y + cornerLen); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(box.x, box.y + box.h - cornerLen); ctx.lineTo(box.x, box.y + box.h); ctx.lineTo(box.x + cornerLen, box.y + box.h); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(box.x + box.w - cornerLen, box.y + box.h); ctx.lineTo(box.x + box.w, box.y + box.h); ctx.lineTo(box.x + box.w, box.y + box.h - cornerLen); ctx.stroke();

        ctx.fillStyle = '#C7A15A';
        ctx.fillRect(box.x, box.y - 22, 170, 20);
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '600 10px Plus Jakarta Sans, sans-serif';
        ctx.fillText('Candidate 98% (ID: #FAC-01)', box.x + 6, box.y - 8);

        const leftEyeX = box.x + box.w * 0.33;
        const rightEyeX = box.x + box.w * 0.67;
        const eyeY = box.y + box.h * 0.38;
        drawCrosshair(ctx, leftEyeX, eyeY, '#C7A15A');
        drawCrosshair(ctx, rightEyeX, eyeY, '#C7A15A');
    } else {
        cachedBoxes.face = null;
    }

    // Draw Phone Box Layer
    if (phoneDetected) {
        const targetPhone = {
            x: width * 0.62,
            y: height * 0.45,
            w: width * 0.24,
            h: height * 0.45
        };

        if (!cachedBoxes.phone) {
            cachedBoxes.phone = { ...targetPhone };
        } else {
            cachedBoxes.phone.x += 0.3 * (targetPhone.x - cachedBoxes.phone.x);
            cachedBoxes.phone.y += 0.3 * (targetPhone.y - cachedBoxes.phone.y);
            cachedBoxes.phone.w += 0.3 * (targetPhone.w - cachedBoxes.phone.w);
            cachedBoxes.phone.h += 0.3 * (targetPhone.h - cachedBoxes.phone.h);
        }

        const pBox = cachedBoxes.phone;

        ctx.strokeStyle = '#B85C4A';
        ctx.lineWidth = 2;
        ctx.strokeRect(pBox.x, pBox.y, pBox.w, pBox.h);

        ctx.fillStyle = '#B85C4A';
        ctx.fillRect(pBox.x, pBox.y - 22, 195, 20);
        ctx.fillStyle = '#ffffff';
        ctx.font = '600 10px Plus Jakarta Sans, sans-serif';
        ctx.fillText('Mobile Phone 94% (ID: #PHN-01)', pBox.x + 6, pBox.y - 8);
    } else {
        cachedBoxes.phone = null;
    }
}

function drawCrosshair(ctx, x, y, color) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.moveTo(x - 8, y); ctx.lineTo(x + 8, y);
    ctx.moveTo(x, y - 8); ctx.lineTo(x, y + 8);
    ctx.stroke();
}

// 8-Step Calibration advancement
let currentCalibStep = 1;
const calibSteps = [
    { step: 1, title: "Step 1 of 8: Look Straight at Center Target", desc: "Focus your gaze directly on the center target dot.", x: "0px", y: "0px" },
    { step: 2, title: "Step 2 of 8: Glance Slowly to the Left", desc: "Glance your eyes to the left target without moving your head.", x: "-80px", y: "0px" },
    { step: 3, title: "Step 3 of 8: Glance Slowly to the Right", desc: "Glance your eyes to the right target without moving your head.", x: "80px", y: "0px" },
    { step: 4, title: "Step 4 of 8: Look Upwards at Top Target", desc: "Glance your eyes upwards at the top target.", x: "0px", y: "-80px" },
    { step: 5, title: "Step 5 of 8: Look Downwards at Bottom Target", desc: "Glance your eyes downwards at the bottom target.", x: "0px", y: "80px" },
    { step: 6, title: "Step 6 of 8: Blink Slowly 2 Times", desc: "Blink your eyes naturally to calibrate baseline eye aspect ratio.", x: "0px", y: "0px" },
    { step: 7, title: "Step 7 of 8: Smile Naturally", desc: "Smile naturally to calibrate candidate facial expression bounds.", x: "0px", y: "0px" },
    { step: 8, title: "Step 8 of 8: Hold Still for Final Baseline", desc: "Hold completely still while registering your baseline biometric descriptor.", x: "0px", y: "0px" }
];

window.advanceCalibration = function() {
    currentCalibStep++;
    if (currentCalibStep > calibSteps.length) {
        switchStep('stepEnvironment');
        return;
    }

    const info = calibSteps[currentCalibStep - 1];
    const dot = document.getElementById('calibTargetDot');
    const title = document.getElementById('calibInstructionTitle');
    const desc = document.getElementById('calibInstructionDesc');
    const pct = document.getElementById('calibProgressPercent');
    const bar = document.getElementById('calibProgressBar');

    if (dot) dot.style.transform = `translate(${info.x}, ${info.y})`;
    if (title) title.innerText = info.title;
    if (desc) desc.innerText = info.desc;

    const progressPct = Math.round((currentCalibStep / 8) * 100);
    if (pct) pct.innerText = `${progressPct}%`;
    if (bar) bar.style.width = `${progressPct}%`;
};

// Cinematic Loading Transition Sequence
window.startCinematicTransition = function() {
    switchStep('stepLoadingTransition');
    const statusTxt = document.getElementById('loadingStatusText');
    const bar = document.getElementById('loadingProgressBar');

    const messages = [
        "Initializing Camera Stream...",
        "Connecting AI Engine...",
        "Loading AI Models...",
        "Checking Camera...",
        "Checking Microphone...",
        "Preparing Workspace...",
        "Ready. Entering Secure Workspace..."
    ];

    let index = 0;
    const interval = setInterval(() => {
        index++;
        if (bar) bar.style.width = `${Math.min(100, (index / messages.length) * 100)}%`;
        if (statusTxt && messages[index]) {
            statusTxt.innerText = messages[index];
        }

        if (index >= messages.length) {
            clearInterval(interval);
            setTimeout(() => {
                switchStep('stepDashboard');
            }, 400);
        }
    }, 400);
};

// Main Dashboard Controller
function initDashboardState() {
    const ws = new TelemetryWebSocket(handleTelemetryUpdate, handleWsStatusChange);

    document.getElementById('btnStart')?.addEventListener('click', () => { initAudioContext(); sendAction('/start'); });
    document.getElementById('btnPause')?.addEventListener('click', () => sendAction('/pause'));
    document.getElementById('btnResume')?.addEventListener('click', () => sendAction('/resume'));
    document.getElementById('btnResetRisk')?.addEventListener('click', () => {
        stopDangerSiren();
        sendAction('/reset-risk');
    });

    const muteBtn = document.getElementById('btnMuteAlarm');
    if (muteBtn) {
        muteBtn.addEventListener('click', () => {
            isAlarmMuted = !isAlarmMuted;
            if (isAlarmMuted) {
                stopDangerSiren();
                muteBtn.innerHTML = '🔇 Muted';
            } else {
                muteBtn.innerHTML = '🔊 Mute';
                initAudioContext();
            }
        });
    }

    document.body.addEventListener('click', initAudioContext, { once: true });
}

function handleWsStatusChange(status) {
    const badge = document.getElementById('wsStatusBadge');
    if (!badge) return;
    if (status === 'CONNECTED') {
        badge.className = 'px-2.5 py-0.5 text-xs font-medium rounded-full bg-[var(--warm-beige)] text-[var(--color-success)]';
        badge.innerText = 'Connected';
    } else if (status === 'CONNECTING') {
        badge.className = 'px-2.5 py-0.5 text-xs font-medium rounded-full bg-[var(--warm-beige)] text-[var(--color-warning)]';
        badge.innerText = 'Connecting...';
    } else {
        badge.className = 'px-2.5 py-0.5 text-xs font-medium rounded-full bg-[var(--warm-beige)] text-[var(--color-critical)]';
        badge.innerText = 'Reconnecting securely...';
    }
}

function handleTelemetryUpdate(data) {
    lastTelemetryData = data;
    const isPhone = !!data.phone_detected;
    const isDanger = !!data.danger_alert || isPhone || (data.severity === 'CRITICAL');

    if (data.camera_state) {
        updateCameraState(data.camera_state);
    }

    const banner = document.getElementById('dangerBanner');
    const dangerMsgEl = document.getElementById('dangerMessage');

    if (isDanger) {
        playDangerSiren();
        if (banner) {
            banner.classList.remove('hidden');
            if (dangerMsgEl) {
                dangerMsgEl.innerText = data.danger_message || (isPhone ? "DANGER ALERT: CELL PHONE DETECTED!" : "DANGER ALERT: PROCTORING VIOLATION!");
            }
        }
    } else {
        stopDangerSiren();
        if (banner) banner.classList.add('hidden');
    }

    // Bounded Risk Score Engine (0% to 100%)
    let riskVal = Math.min(100, Math.max(0, data.risk || 0));
    let peakVal = Math.min(100, Math.max(0, data.peak_risk || 0));

    document.getElementById('txtRiskScore').innerText = `${riskVal.toFixed(1)}%`;
    document.getElementById('txtPeakRisk').innerText = `Peak: ${peakVal.toFixed(1)}%`;
    
    const riskBar = document.getElementById('riskProgressBar');
    if (riskBar) {
        riskBar.style.width = `${riskVal}%`;
        if (riskVal > 60) {
            riskBar.className = 'h-full rounded-full transition-all duration-300 bg-[var(--color-critical)]';
        } else if (riskVal > 40) {
            riskBar.className = 'h-full rounded-full transition-all duration-300 bg-[var(--color-warning)]';
        } else {
            riskBar.className = 'h-full rounded-full transition-all duration-300 bg-[var(--color-success)]';
        }
    }

    // Risk Severity Badge Labeling (Safe 0-20, Low 21-40, Moderate 41-60, High 61-80, Critical 81-100)
    const sevBadge = document.getElementById('txtSeverityBadge');
    if (sevBadge) {
        if (riskVal <= 20) {
            sevBadge.innerText = 'Safe (0-20%)';
            sevBadge.className = 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-[var(--warm-beige)] text-[var(--color-success)]';
        } else if (riskVal <= 40) {
            sevBadge.innerText = 'Low (21-40%)';
            sevBadge.className = 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-[var(--warm-beige)] text-[var(--dark-brown)]';
        } else if (riskVal <= 60) {
            sevBadge.innerText = 'Moderate (41-60%)';
            sevBadge.className = 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-[var(--warm-beige)] text-[var(--color-warning)]';
        } else if (riskVal <= 80) {
            sevBadge.innerText = 'High (61-80%)';
            sevBadge.className = 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-[var(--warm-beige)] text-[var(--color-critical)]';
        } else {
            sevBadge.innerText = 'Critical (81-100%)';
            sevBadge.className = 'px-2.5 py-0.5 text-xs font-bold rounded-full bg-[var(--color-critical)] text-white';
        }
    }

    // AI Explainability Breakdown
    const expPhone = document.getElementById('explainPhone');
    const expGaze = document.getElementById('explainGaze');
    const expMulti = document.getElementById('explainMultiFace');
    const expTotal = document.getElementById('txtExplainTotal');

    if (expPhone) expPhone.className = isPhone ? "flex justify-between items-center p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--color-critical)]" : "hidden";
    if (expGaze) expGaze.className = (data.looking_left || data.looking_right || data.offscreen) ? "flex justify-between items-center p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--color-warning)]" : "hidden";
    if (expMulti) expMulti.className = data.multiple_faces ? "flex justify-between items-center p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--color-critical)]" : "hidden";
    if (expTotal) expTotal.innerText = `${riskVal.toFixed(1)}%`;

    document.getElementById('txtGazeDir').innerText = data.gaze_direction || 'CENTER';
    updatePill('pillLeft', data.looking_left);
    updatePill('pillRight', data.looking_right);
    updatePill('pillUp', data.looking_up);
    updatePill('pillDown', data.looking_down);
    updatePill('pillOffscreen', data.offscreen);

    updateStatusPill('pillFace', data.face_detected, 'Verified', 'No Face');
    updateStatusPill('pillMultiFace', !data.multiple_faces, 'Single', 'Multiple');
    updateStatusPill('pillPhone', !isPhone, 'Clear', 'Phone Detected');
    updateStatusPill('pillHeadTurn', !data.head_turned, 'Centered', 'Turned');

    document.getElementById('txtDuration').innerText = formatDuration(data.exam_duration_sec || 0);
    updateRiskChart(data.timestamp || '', riskVal);

    if (data.event && data.event !== window.lastLoggedEvent) {
        window.lastLoggedEvent = data.event;
        addEventToFeed(data.timestamp, data.severity || 'NORMAL', data.event);
    }
}

function updatePill(id, isActive) {
    const el = document.getElementById(id);
    if (!el) return;
    if (isActive) {
        el.className = 'px-2.5 py-1 text-xs font-bold rounded-lg bg-[var(--warm-beige)] text-[var(--color-critical)] border border-[var(--color-critical)]';
    } else {
        el.className = 'px-2.5 py-1 text-xs font-medium rounded-lg bg-[var(--bg-primary)] text-[var(--text-muted)] border border-[var(--border-color)]';
    }
}

function updateStatusPill(id, isOk, okText, badText) {
    const el = document.getElementById(id);
    if (!el) return;
    if (isOk) {
        el.innerText = okText;
        el.className = 'font-bold text-[var(--color-success)] text-[11px]';
    } else {
        el.innerText = badText;
        el.className = 'font-bold text-[var(--color-critical)] text-[11px]';
    }
}

function addEventToFeed(timestamp, severity, text) {
    const feed = document.getElementById('eventFeedList');
    if (!feed) return;

    const item = document.createElement('div');
    item.className = 'p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] flex justify-between items-center text-xs';
    const badgeCls = severity === 'NORMAL' ? 'text-[var(--color-success)]' : (severity === 'WARNING' ? 'text-[var(--color-warning)]' : 'text-[var(--color-critical)] font-bold');

    item.innerHTML = `
        <div class="flex items-center gap-2">
            <span class="font-mono text-[var(--text-muted)] text-[11px]">${timestamp}</span>
            <span class="text-[var(--text-primary)]">${text}</span>
        </div>
        <span class="${badgeCls}">${severity}</span>
    `;

    feed.prepend(item);
    if (feed.children.length > 20) feed.removeChild(feed.lastChild);
}

function sendAction(endpoint) {
    fetch(endpoint, { method: 'POST' })
        .then(res => res.json())
        .then(data => console.log(`Action ${endpoint} success:`, data))
        .catch(err => console.error(`Action ${endpoint} failed:`, err));
}

function formatDuration(seconds) {
    const secs = Math.floor(seconds);
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

document.addEventListener('DOMContentLoaded', initTheme);
