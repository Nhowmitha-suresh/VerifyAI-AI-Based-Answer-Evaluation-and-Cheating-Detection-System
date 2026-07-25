import React, { useState, useEffect, useRef } from 'react';
import { 
  Shield, AlertTriangle, CheckCircle, Camera, RefreshCw, RotateCcw, 
  FileText, Activity, Eye, User, Volume2, Monitor, Hand, Cpu
} from 'lucide-react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend, Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler
);

export default function App() {
  const [sessionTime, setSessionTime] = useState(0);
  const [fps, setFps] = useState(30);
  const [riskScore, setRiskScore] = useState(0);
  const [severity, setSeverity] = useState('NORMAL');
  const [explanation, setExplanation] = useState('Candidate behavior normal and centered.');
  const [scoreHistory, setScoreHistory] = useState([0]);
  const [timeLabels, setTimeLabels] = useState(['00:00']);

  const [telemetry, setTelemetry] = useState({
    phone_status: 'CLEAR', phone_detected: false,
    window_status: 'FOCUSED', window_switched: false,
    gaze_status: 'CENTER', offscreen: false, rapid_scan: false,
    head_status: 'NORMAL', headturn: false, lap_glance: false,
    face_status: 'VERIFIED', multiface: false, occlusion: false,
    hand_status: 'CLEAR', handnear: false,
    audio_status: 'QUIET', othervoice: false,
    ear_status: 'ACTIVE', eyes_closed: false
  });

  const videoRef = useRef(null);

  // Session Timer Loop
  useEffect(() => {
    const timer = setInterval(() => setSessionTime(prev => prev + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  // WebCam Stream Initialization
  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch(err => {
        console.warn("Local webcam access warning:", err);
      });
  }, []);

  // Browser Window Focus / Tab Switch Proctoring Detection
  useEffect(() => {
    const handleBlur = () => {
      setTelemetry(prev => ({
        ...prev,
        window_status: 'UNFOCUSED (TAB SWITCH)',
        window_switched: true
      }));
      setRiskScore(prev => prev + 10);
      setSeverity('WARNING');
      setExplanation('Candidate switched active browser window / lost focus.');
    };

    const handleFocus = () => {
      setTelemetry(prev => ({
        ...prev,
        window_status: 'FOCUSED',
        window_switched: false
      }));
    };

    window.addEventListener('blur', handleBlur);
    window.addEventListener('focus', handleFocus);
    return () => {
      window.removeEventListener('blur', handleBlur);
      window.removeEventListener('focus', handleFocus);
    };
  }, []);

  // Live Telemetry Sync from FastAPI Backend Server
  useEffect(() => {
    const fetchLiveTelemetry = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/telemetry/live');
        if (res.ok) {
          const data = await res.json();
          setTelemetry(prev => ({ ...prev, ...data }));
          if (data.risk_score !== undefined) {
            setRiskScore(data.risk_score);
            setScoreHistory(prev => [...prev.slice(-25), data.risk_score]);
            setTimeLabels(prev => [...prev.slice(-25), formatTime(sessionTime)]);
          }
          if (data.severity) setSeverity(data.severity);
          if (data.explanation) setExplanation(data.explanation);
        }
      } catch (e) {
        // Backend offline fallback
      }
    };

    const interval = setInterval(fetchLiveTelemetry, 300);
    return () => clearInterval(interval);
  }, [sessionTime]);

  // Chart Configuration
  const chartData = {
    labels: timeLabels,
    datasets: [
      {
        label: 'Risk Index (0-100%)',
        data: scoreHistory,
        borderColor: severity === 'CRITICAL' ? '#ef4444' : (severity === 'WARNING' ? '#f59e0b' : '#06b6d4'),
        backgroundColor: severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(6, 182, 212, 0.15)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 2
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { min: 0, max: 40, grid: { color: 'rgba(55, 65, 81, 0.4)' }, ticks: { color: '#9ca3af' } },
      x: { grid: { display: false }, ticks: { color: '#9ca3af', maxTicksLimit: 6 } }
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getSeverityBadge = () => {
    if (riskScore >= 28 || telemetry.phone_detected) {
      return { label: 'CRITICAL ALARM', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.2)' };
    } else if (riskScore >= 15 || telemetry.window_switched || telemetry.offscreen) {
      return { label: 'WARNING - SUSPICIOUS', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.2)' };
    }
    return { label: 'MONITORING - NORMAL', color: '#10b981', bg: 'rgba(16, 185, 129, 0.2)' };
  };

  const badge = getSeverityBadge();

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
      {/* Top Header Banner */}
      <header className="glass-panel" style={{ padding: '16px 24px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Shield style={{ color: '#06b6d4', width: '28px', height: '28px' }} />
            <h1 style={{ fontSize: '22px', fontWeight: '800', letterSpacing: '-0.5px', background: 'linear-gradient(90deg, #06b6d4, #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              VerifyAI Proctoring Engine
            </h1>
          </div>
          <p style={{ fontSize: '13px', color: '#9ca3af', marginTop: '4px' }}>
            Commercial Real-Time Candidate Monitoring Platform • Session ID: <code style={{ color: '#06b6d4' }}>#EXAM-2026-9042</code>
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '12px', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Session Duration</div>
            <div style={{ fontSize: '18px', fontWeight: '700', fontFamily: 'monospace', color: '#06b6d4' }}>{formatTime(sessionTime)}</div>
          </div>
          <div style={{ padding: '8px 16px', borderRadius: '10px', background: badge.bg, border: `1px solid ${badge.color}`, color: badge.color, fontWeight: '700', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="pulse-dot" style={{ backgroundColor: badge.color }}></span>
            {badge.label}
          </div>
        </div>
      </header>

      {/* Main Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
        {/* Left Column: Video Feed & Risk Gauge */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Webcam Video Container */}
          <div className="glass-panel" style={{ padding: '16px', position: 'relative' }}>
            <div style={{ position: 'relative', width: '100%', borderRadius: '12px', overflow: 'hidden', background: '#000', border: '1px solid var(--border-color)', aspectRatio: '16/9' }}>
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted 
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
              
              {/* Overlay HUD Watermark */}
              <div style={{ position: 'absolute', top: '16px', left: '16px', background: 'rgba(9, 13, 22, 0.8)', backdropFilter: 'blur(8px)', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', border: '1px solid rgba(6, 182, 212, 0.3)', color: '#06b6d4', fontWeight: '600' }}>
                AI PROCTOR HUD ACTIVE • {fps} FPS
              </div>

              <div style={{ position: 'absolute', bottom: '16px', right: '16px', background: 'rgba(9, 13, 22, 0.8)', backdropFilter: 'blur(8px)', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', color: '#9ca3af', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                Active Window: {telemetry.window_status}
              </div>
            </div>

            {/* Risk Index Progress Gauge */}
            <div style={{ marginTop: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '13px', fontWeight: '700' }}>
                <span>CANDIDATE RISK INDEX</span>
                <span style={{ color: badge.color }}>{riskScore.toFixed(1)} / 28.0 ({Math.min(100, (riskScore / 28) * 100).toFixed(0)}%)</span>
              </div>
              <div style={{ height: '12px', borderRadius: '6px', background: '#111827', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
                <div 
                  style={{ 
                    height: '100%', 
                    width: `${Math.min(100, (riskScore / 28) * 100)}%`, 
                    backgroundColor: badge.color,
                    transition: 'width 0.4s ease, background-color 0.4s ease'
                  }}
                />
              </div>
            </div>
          </div>

          {/* Risk Score Trend Chart */}
          <div className="glass-panel" style={{ padding: '20px', height: '220px' }}>
            <div style={{ fontSize: '13px', fontWeight: '700', color: '#06b6d4', textTransform: 'uppercase', marginBottom: '12px' }}>
              Real-Time Risk Index Trend Timeline
            </div>
            <div style={{ height: '150px' }}>
              <Line data={chartData} options={chartOptions} />
            </div>
          </div>
        </div>

        {/* Right Column: Telemetry & Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Telemetry Indicator Card List */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ fontSize: '14px', fontWeight: '700', color: '#06b6d4', textTransform: 'uppercase', paddingBottom: '12px', borderBottom: '1px solid var(--border-color)', marginBottom: '16px' }}>
              Telemetry Monitor
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <TelemetryRow icon={Monitor} label="Mobile Phone AI" val={telemetry.phone_status} isAlert={telemetry.phone_detected} />
              <TelemetryRow icon={Activity} label="Window Focus" val={telemetry.window_status} isAlert={telemetry.window_switched} />
              <TelemetryRow icon={Eye} label="Gaze Direction" val={telemetry.gaze_status} isAlert={telemetry.offscreen || telemetry.rapid_scan} />
              <TelemetryRow icon={User} label="Head Orientation" val={telemetry.head_status} isAlert={telemetry.headturn || telemetry.lap_glance} />
              <TelemetryRow icon={Shield} label="Face Verification" val={telemetry.face_status} isAlert={telemetry.multiface || telemetry.occlusion} />
              <TelemetryRow icon={Hand} label="Hand Proxy" val={telemetry.hand_status} isAlert={telemetry.handnear} />
              <TelemetryRow icon={Volume2} label="Audio Collusion" val={telemetry.audio_status} isAlert={telemetry.othervoice} />
              <TelemetryRow icon={Cpu} label="Drowsiness/Blink" val={telemetry.ear_status} isAlert={telemetry.eyes_closed} />
            </div>
          </div>

          {/* Explainability Box */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ fontSize: '13px', fontWeight: '700', color: '#06b6d4', textTransform: 'uppercase', marginBottom: '8px' }}>
              Explainable AI Rationale
            </div>
            <p style={{ fontSize: '13px', color: '#d1d5db', lineHeight: '1.5' }}>
              {explanation}
            </p>
          </div>

          {/* Control Toolbar */}
          <div className="glass-panel" style={{ padding: '16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <button className="glass-card" style={{ padding: '10px', color: '#f9fafb', fontSize: '12px', fontWeight: '600', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', cursor: 'pointer' }} onClick={() => alert("Gaze baseline recalibrated!")}>
              <RefreshCw size={14} color="#06b6d4" /> Recalibrate
            </button>
            <button className="glass-card" style={{ padding: '10px', color: '#f9fafb', fontSize: '12px', fontWeight: '600', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', cursor: 'pointer' }} onClick={() => { setRiskScore(0); setTelemetry(prev => ({ ...prev, window_switched: false, window_status: 'FOCUSED' })); }}>
              <RotateCcw size={14} color="#f59e0b" /> Reset Score
            </button>
            <button className="glass-card" style={{ padding: '10px', color: '#f9fafb', fontSize: '12px', fontWeight: '600', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', cursor: 'pointer' }} onClick={() => alert("Evidence snapshot saved!")}>
              <Camera size={14} color="#10b981" /> Snapshot
            </button>
            <a href="http://localhost:8000/api/report" target="_blank" rel="noreferrer" className="glass-card" style={{ padding: '10px', color: '#f9fafb', fontSize: '12px', fontWeight: '600', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', textDecoration: 'none' }}>
              <FileText size={14} color="#3b82f6" /> Report HTML
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

function TelemetryRow({ icon: Icon, label, val, isAlert }) {
  return (
    <div className="glass-card" style={{ padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#d1d5db' }}>
        <span className="pulse-dot" style={{ backgroundColor: isAlert ? '#ef4444' : '#10b981' }}></span>
        <Icon size={14} color="#9ca3af" />
        <span>{label}</span>
      </div>
      <span style={{ fontSize: '12px', fontWeight: '700', color: isAlert ? '#ef4444' : '#10b981' }}>
        {val}
      </span>
    </div>
  );
}
