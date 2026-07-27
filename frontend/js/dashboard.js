/**
 * Main Frontend Dashboard Logic & Event Handlers.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Live Chart
    initRiskChart('riskChartCanvas');

    // Initialize WebSocket
    const ws = new TelemetryWebSocket(handleTelemetryUpdate, handleWsStatusChange);

    // Event Listeners for Controls
    document.getElementById('btnStart')?.addEventListener('click', () => sendAction('/start'));
    document.getElementById('btnPause')?.addEventListener('click', () => sendAction('/pause'));
    document.getElementById('btnResume')?.addEventListener('click', () => sendAction('/resume'));
    document.getElementById('btnStop')?.addEventListener('click', () => sendAction('/stop'));
    document.getElementById('btnSnapshot')?.addEventListener('click', () => sendAction('/snapshot'));
    document.getElementById('btnRecalibrate')?.addEventListener('click', () => sendAction('/recalibrate'));
    document.getElementById('btnResetRisk')?.addEventListener('click', () => sendAction('/reset-risk'));

    // Fetch initial snapshots gallery
    loadSnapshotGallery();
});

function handleWsStatusChange(status) {
    const badge = document.getElementById('wsStatusBadge');
    if (!badge) return;
    if (status === 'CONNECTED') {
        badge.className = 'px-3 py-1 text-xs font-semibold rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 flex items-center gap-1.5';
        badge.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> LIVE WEBSOCKET';
    } else if (status === 'CONNECTING') {
        badge.className = 'px-3 py-1 text-xs font-semibold rounded-full bg-amber-950/80 text-amber-400 border border-amber-500/40 flex items-center gap-1.5';
        badge.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span> CONNECTING...';
    } else {
        badge.className = 'px-3 py-1 text-xs font-semibold rounded-full bg-rose-950/80 text-rose-400 border border-rose-500/40 flex items-center gap-1.5';
        badge.innerHTML = '<span class="w-2 h-2 rounded-full bg-rose-500"></span> DISCONNECTED';
    }
}

function handleTelemetryUpdate(data) {
    // 1. Update Risk Score Gauge & Progress Bar
    const riskVal = data.risk || 0;
    const peakVal = data.peak_risk || 0;
    const severity = data.severity || 'NORMAL';

    document.getElementById('txtRiskScore').innerText = `${riskVal}%`;
    document.getElementById('txtPeakRisk').innerText = `PEAK: ${peakVal}%`;
    
    const riskBar = document.getElementById('riskProgressBar');
    if (riskBar) {
        riskBar.style.width = `${Math.min(100, Math.max(0, riskVal))}%`;
        if (severity === 'CRITICAL') {
            riskBar.className = 'h-full rounded-full transition-all duration-300 bg-red-600 shadow-[0_0_15px_rgba(239,68,68,0.8)]';
        } else if (severity === 'HIGH_RISK') {
            riskBar.className = 'h-full rounded-full transition-all duration-300 bg-orange-500 shadow-[0_0_15px_rgba(249,115,22,0.8)]';
        } else if (severity === 'WARNING') {
            riskBar.className = 'h-full rounded-full transition-all duration-300 bg-amber-400';
        } else {
            riskBar.className = 'h-full rounded-full transition-all duration-300 bg-emerald-500';
        }
    }

    const sevBadge = document.getElementById('txtSeverityBadge');
    if (sevBadge) {
        sevBadge.innerText = severity;
        if (severity === 'CRITICAL' || severity === 'HIGH_RISK') {
            sevBadge.className = 'px-2.5 py-0.5 text-xs font-extrabold rounded bg-red-950 text-red-400 border border-red-500/40 animate-pulse';
        } else if (severity === 'WARNING') {
            sevBadge.className = 'px-2.5 py-0.5 text-xs font-bold rounded bg-amber-950 text-amber-400 border border-amber-500/40';
        } else {
            sevBadge.className = 'px-2.5 py-0.5 text-xs font-bold rounded bg-emerald-950 text-emerald-400 border border-emerald-500/40';
        }
    }

    // 2. Update Gaze Direction Pills
    document.getElementById('txtGazeDir').innerText = data.gaze_direction || 'CENTER';
    updatePill('pillLeft', data.looking_left);
    updatePill('pillRight', data.looking_right);
    updatePill('pillUp', data.looking_up);
    updatePill('pillDown', data.looking_down);
    updatePill('pillOffscreen', data.offscreen);
    updatePill('pillRapid', data.rapid_scan);

    // 3. Update Status Indicators
    updateStatusPill('pillFace', data.face_detected, 'VERIFIED', 'NO FACE', true);
    updateStatusPill('pillMultiFace', !data.multiple_faces, 'SINGLE', 'MULTI-FACE', false);
    updateStatusPill('pillPhone', !data.phone_detected, 'CLEAR', 'CELL PHONE DETECTED!', false);
    updateStatusPill('pillHeadTurn', !data.head_turned, 'CENTERED', 'HEAD TURNED', false);

    // 4. Counters & System Metrics
    document.getElementById('txtBlinks').innerText = data.blink_count || 0;
    document.getElementById('txtFps').innerText = `${data.fps || 0} FPS`;
    document.getElementById('txtDuration').innerText = formatDuration(data.exam_duration_sec || 0);
    document.getElementById('txtCpu').innerText = `${data.cpu_percent || 0}%`;
    document.getElementById('txtRam').innerText = `${data.ram_percent || 0}%`;
    document.getElementById('txtActiveWindow').innerText = data.active_window || 'Exam Browser';

    // 5. Update Live Chart
    updateRiskChart(data.timestamp || '', riskVal);

    // 6. Update Event Feed if new event
    if (data.event && data.event !== window.lastLoggedEvent) {
        window.lastLoggedEvent = data.event;
        addEventToFeed(data.timestamp, severity, data.event);
    }
}

function updatePill(id, isActive) {
    const el = document.getElementById(id);
    if (!el) return;
    if (isActive) {
        el.className = 'px-2.5 py-1 text-xs font-bold rounded bg-red-900/80 text-red-200 border border-red-500/60 animate-pulse';
    } else {
        el.className = 'px-2.5 py-1 text-xs font-medium rounded bg-slate-800/80 text-slate-400 border border-slate-700/60';
    }
}

function updateStatusPill(id, isOk, okText, badText, okWhenTrue) {
    const el = document.getElementById(id);
    if (!el) return;
    const isGood = okWhenTrue ? isOk : isOk;
    if (isGood) {
        el.innerText = okText;
        el.className = 'px-2 py-0.5 text-xs font-bold rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/40';
    } else {
        el.innerText = badText;
        el.className = 'px-2 py-0.5 text-xs font-bold rounded bg-red-950/80 text-red-400 border border-red-500/40 animate-pulse';
    }
}

function addEventToFeed(timestamp, severity, text) {
    const feed = document.getElementById('eventFeedList');
    if (!feed) return;

    const item = document.createElement('div');
    item.className = 'p-2.5 rounded bg-slate-800/60 border border-slate-700/50 flex justify-between items-center text-xs animate-fade-in';
    
    const badgeCls = severity === 'NORMAL' ? 'text-emerald-400' : (severity === 'WARNING' ? 'text-amber-400' : 'text-red-400 font-bold');

    item.innerHTML = `
        <div class="flex items-center gap-2">
            <span class="font-mono text-slate-400 text-[11px]">${timestamp}</span>
            <span class="text-slate-200">${text}</span>
        </div>
        <span class="${badgeCls}">${severity}</span>
    `;

    feed.prepend(item);
    if (feed.children.length > 20) feed.removeChild(feed.lastChild);
}

function sendAction(endpoint) {
    fetch(endpoint, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            console.log(`Action ${endpoint} success:`, data);
            if (endpoint === '/snapshot') {
                setTimeout(loadSnapshotGallery, 500);
            }
        })
        .catch(err => console.error(`Action ${endpoint} failed:`, err));
}

function loadSnapshotGallery() {
    fetch('/snapshots')
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('snapshotGallery');
            if (!container || !data.snapshots) return;
            container.innerHTML = '';

            data.snapshots.slice(-8).reverse().forEach(snap => {
                const card = document.createElement('div');
                card.className = 'group relative rounded border border-slate-700/60 overflow-hidden bg-slate-800/80 hover:border-blue-500 transition-all';
                card.innerHTML = `
                    <img src="${snap.url}" class="w-full h-20 object-cover">
                    <div class="p-1 text-[10px] text-slate-300 font-mono text-center truncate">${snap.reason}</div>
                `;
                container.appendChild(card);
            });
        })
        .catch(err => console.error('Failed to load snapshots:', err));
}

function formatDuration(seconds) {
    const secs = Math.floor(seconds);
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}
