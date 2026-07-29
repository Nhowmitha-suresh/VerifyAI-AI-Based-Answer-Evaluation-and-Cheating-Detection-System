"""
Interactive HTML Session Audit Report Generator.
Renders executive dashboard, violation breakdown, explainability logs, embedded incident videos & gaze heatmaps.
"""

import os
import datetime
import collections
from typing import Dict, List, Any
from .config import REPORT_FILE, SNAPSHOT_DIR, ALARM_HIGH
from .logger import all_logged_events, logger


def generate_html_report(incident_logs: List[Dict[str, Any]] = None, gaze_heatmap_file: str = None, analytics_summary: Dict[str, Any] = None):
    logger.info(f"Generating session audit report: {REPORT_FILE}...")

    total_events = len(all_logged_events)
    scores = [e["total"] for e in all_logged_events] if all_logged_events else [0.0]
    max_score = max(scores)
    
    counts = collections.Counter([e["label"] for e in all_logged_events])
    
    snapshots = []
    if os.path.exists(SNAPSHOT_DIR):
        snapshots = [f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".jpg") and "heatmap" not in f]

    incident_videos = incident_logs or []

    heatmap_path = gaze_heatmap_file or "gaze_heatmap_latest.jpg"
    has_heatmap = os.path.exists(os.path.join(SNAPSHOT_DIR, heatmap_path)) or os.path.exists(heatmap_path)

    verdict = "FLAGGED HIGH RISK / HIGH VIOLATION RATE" if max_score >= ALARM_HIGH else ("SUSPICIOUS" if max_score >= 15.0 else "PASSED / LOW RISK")
    verdict_color = "#ef4444" if max_score >= ALARM_HIGH else ("#f59e0b" if max_score >= 15.0 else "#10b981")

    attn_pct = analytics_summary.get("attention_percentage", 95.0) if analytics_summary else 95.0
    focus_pct = analytics_summary.get("focus_percentage", 92.0) if analytics_summary else 92.0

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise AI Proctoring Audit Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg: #0b0f19;
            --panel: #151c2c;
            --card: #1e293b;
            --border: #334155;
            --accent: #38bdf8;
            --text: #f8fafc;
            --text-dim: #94a3b8;
        }}
        body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 24px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: var(--panel); border-radius: 16px; padding: 32px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); border: 1px solid var(--border); }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border); padding-bottom: 20px; margin-bottom: 24px; }}
        h1 {{ color: var(--accent); margin: 0; font-size: 26px; letter-spacing: -0.5px; }}
        .verdict-badge {{ padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 14px; background: {verdict_color}22; color: {verdict_color}; border: 1px solid {verdict_color}; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid var(--border); border-left: 4px solid var(--accent); }}
        .card h3 {{ margin: 0 0 8px 0; font-size: 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }}
        .card .val {{ font-size: 30px; font-weight: 800; color: var(--text); }}
        .section {{ margin-top: 36px; }}
        h2 {{ font-size: 18px; color: var(--accent); margin-bottom: 16px; border-left: 3px solid var(--accent); padding-left: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; background: var(--card); border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 14px 18px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; }}
        th {{ background: #0f172a; color: var(--accent); text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }}
        tr:hover {{ background: #283548; }}
        .badge {{ padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; text-transform: uppercase; }}
        .badge-critical {{ background: #ef444422; color: #ef4444; border: 1px solid #ef4444; }}
        .badge-warning {{ background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b; }}
        .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-top: 16px; }}
        .gallery-item {{ background: var(--card); border-radius: 10px; padding: 10px; border: 1px solid var(--border); }}
        .gallery-item img, .gallery-item video {{ width: 100%; border-radius: 6px; border: 1px solid var(--border); }}
        .chart-container {{ background: var(--card); padding: 24px; border-radius: 12px; border: 1px solid var(--border); margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>VerifyAI Enterprise Proctoring Audit Report</h1>
                <p style="color: var(--text-dim); margin: 6px 0 0 0; font-size: 13px;">Generated on: {datetime.datetime.now().strftime("%B %d, %Y - %H:%M:%S")}</p>
            </div>
            <div class="verdict-badge">{verdict}</div>
        </div>
        
        <div class="stats-grid">
            <div class="card">
                <h3>Total Incidents</h3>
                <div class="val">{total_events}</div>
            </div>
            <div class="card" style="border-left-color: {verdict_color};">
                <h3>Peak Risk Score</h3>
                <div class="val">{max_score:.1f}</div>
            </div>
            <div class="card">
                <h3>Candidate Attention</h3>
                <div class="val" style="color: #10b981;">{attn_pct:.1f}%</div>
            </div>
            <div class="card">
                <h3>Focus Rating</h3>
                <div class="val" style="color: #38bdf8;">{focus_pct:.1f}%</div>
            </div>
        </div>

        <div class="section">
            <h2>Explainable AI Violation Breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Violation Category</th>
                        <th>Incident Count</th>
                        <th>Severity Level</th>
                        <th>Explainable AI Rationale</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f"<tr><td><strong>{k.upper()}</strong></td><td>{v}</td><td><span class='badge {'badge-critical' if k in ['phone_detected', 'window_switch', 'phone_lap_combo', 'phone_window_combo'] else 'badge-warning'}'>{'CRITICAL' if k in ['phone_detected', 'window_switch', 'phone_lap_combo', 'phone_window_combo'] else 'HIGH'}</span></td><td>Multi-signal rule match for {k.replace('_', ' ')}</td></tr>" for k,v in counts.items()]) or "<tr><td colspan='4'>Clean proctoring session. No violations recorded.</td></tr>"}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Risk Trend Analysis</h2>
            <div class="chart-container">
                <canvas id="riskChart" height="90"></canvas>
            </div>
        </div>

        {"<div class='section'><h2>Eye Heatmap & Gaze Attention Center</h2><div class='gallery-item' style='max-width:600px;'><img src='snapshots/gaze_heatmap_latest.jpg' alt='Gaze Heatmap'><p style='font-size:13px;color:var(--text-dim);margin-top:8px;'>Session Spatial Gaze Heatmap Density</p></div></div>" if has_heatmap else ""}

        {"<div class='section'><h2>Recorded Video Evidence Clips (10s Pre/Post Incident)</h2><div class='gallery'>" + ''.join([f"<div class='gallery-item'><video controls src='snapshots/{os.path.basename(v['video_path'])}'></video><p style='font-size:12px;color:var(--text-dim);margin:6px 0 0 0;'><strong>{v['reason'].upper()}</strong> (Score: {v['score']:.1f})</p></div>" for v in incident_videos]) + "</div></div>" if incident_videos else ""}

        {"<div class='section'><h2>Snapshot Gallery</h2><div class='gallery'>" + ''.join([f"<div class='gallery-item'><img src='snapshots/{s}' alt='Snapshot'><p style='font-size:12px;color:var(--text-dim);margin:6px 0 0 0;'>{s}</p></div>" for s in snapshots[:8]]) + "</div></div>" if snapshots else ""}
    </div>

    <script>
        const ctx = document.getElementById('riskChart').getContext('2d');
        const eventData = {[e['total'] for e in all_logged_events[-30:]] if all_logged_events else [0]};
        const labels = {[i for i in range(1, len(all_logged_events[-30:]) + 1)] if all_logged_events else [1]};

        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Cumulative Risk Index',
                    data: eventData,
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: '#334155' }} }},
                    x: {{ grid: {{ color: '#334155' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Saved audit report to file:///{os.path.abspath(REPORT_FILE)}")
    except Exception as e:
        logger.error(f"Failed to write HTML report: {e}")
