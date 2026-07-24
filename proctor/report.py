"""
Interactive HTML Session Audit Report Generator.
"""

import os
import datetime
import collections
from .config import REPORT_FILE, SNAPSHOT_DIR, ALARM_HIGH
from .logger import all_logged_events, logger

def generate_html_report():
    logger.info(f"Generating session report: {REPORT_FILE}...")
    total_events = len(all_logged_events)
    max_score = max([e["total"] for e in all_logged_events], default=0.0)
    
    counts = collections.Counter([e["label"] for e in all_logged_events])
    snapshots = [os.path.join(SNAPSHOT_DIR, f) for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".jpg")] if os.path.exists(SNAPSHOT_DIR) else []

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Proctoring Session Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 24px; }}
        .container {{ max-width: 1100px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h1 {{ color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 12px; margin-top: 0; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 24px 0; }}
        .card {{ background: #0f172a; padding: 20px; border-radius: 8px; border-left: 4px solid #38bdf8; }}
        .card h3 {{ margin: 0 0 8px 0; font-size: 14px; color: #94a3b8; text-transform: uppercase; }}
        .card .val {{ font-size: 28px; font-weight: bold; color: #f8fafc; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #38bdf8; }}
        tr:hover {{ background: #283548; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block; }}
        .badge-high {{ background: #ef4444; color: #fff; }}
        .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-top: 20px; }}
        .gallery img {{ width: 100%; border-radius: 8px; border: 2px solid #334155; transition: transform 0.2s; }}
        .gallery img:hover {{ transform: scale(1.03); border-color: #38bdf8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>NegoSphere AI Proctoring Audit Report</h1>
        <p style="color: #94a3b8;">Generated on: {datetime.datetime.now().strftime("%B %d, %Y - %H:%M:%S")}</p>
        
        <div class="stats-grid">
            <div class="card">
                <h3>Total Incidents</h3>
                <div class="val">{total_events}</div>
            </div>
            <div class="card" style="border-color: {'#ef4444' if max_score >= ALARM_HIGH else '#10b981'};">
                <h3>Peak Risk Score</h3>
                <div class="val">{max_score:.1f}</div>
            </div>
            <div class="card">
                <h3>Evidence Snapshots</h3>
                <div class="val">{len(snapshots)}</div>
            </div>
            <div class="card">
                <h3>Session Verdict</h3>
                <div class="val" style="color: {'#ef4444' if max_score >= ALARM_HIGH else '#10b981'};">
                    {"FLAGGED HIGH RISK" if max_score >= ALARM_HIGH else "PASS / LOW RISK"}
                </div>
            </div>
        </div>

        <h2>Violation Breakdown</h2>
        <table>
            <thead>
                <tr>
                    <th>Event Category</th>
                    <th>Count</th>
                    <th>Severity Rating</th>
                </tr>
            </thead>
            <tbody>
                {''.join([f"<tr><td>{k.upper()}</td><td>{v}</td><td>{'CRITICAL' if k in ['phone_detected', 'window_switch'] else 'HIGH'}</td></tr>" for k,v in counts.items()]) or "<tr><td colspan='3'>No violations recorded.</td></tr>"}
            </tbody>
        </table>

        <h2>Incident Timeline (Recent 20)</h2>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Event Type</th>
                    <th>Event Score</th>
                    <th>Cumulative Risk</th>
                </tr>
            </thead>
            <tbody>
                {''.join([f"<tr><td>{e['datetime']}</td><td><span class='badge badge-high'>{e['label'].upper()}</span></td><td>+{e['score']}</td><td>{e['total']:.1f}</td></tr>" for e in all_logged_events[-20:]]) or "<tr><td colspan='4'>Clean session.</td></tr>"}
            </tbody>
        </table>

        {"<h2>Evidence Gallery</h2><div class='gallery'>" + ''.join([f"<div><img src='{os.path.basename(s)}' alt='Snapshot'><p style='font-size:12px;color:#94a3b8;'>{os.path.basename(s)}</p></div>" for s in snapshots]) + "</div>" if snapshots else ""}
    </div>
</body>
</html>
"""
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Saved report to file:///{os.path.abspath(REPORT_FILE)}")
    except Exception as e:
        logger.error(f"Failed to write HTML report: {e}")
