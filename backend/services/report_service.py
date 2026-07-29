"""
HTML Exam Audit Report Generation Service.
Compiles session statistics, violation timelines, risk charts, and snapshot galleries
into self-contained reports/proctor_report.html.
"""

import os
import datetime
from typing import List, Dict, Any
from backend.core.settings import settings
from backend.core.logger import logger
from backend.core.app_state import app_state

class ReportService:
    @staticmethod
    def generate_html_report() -> str:
        report_path = settings.REPORT_FILE
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        events = app_state.events
        snapshots = app_state.snapshots
        duration_sec = app_state.get_duration()
        duration_str = str(datetime.timedelta(seconds=int(duration_sec)))
        peak_risk = app_state.peak_risk_score
        avg_risk = round(sum([e.get("total_risk", 0.0) for e in events]) / max(1, len(events)), 1) if events else 0.0

        # Build snapshot gallery items
        snapshot_html = ""
        for s in snapshots:
            snapshot_html += f"""
            <div class="border rounded-lg p-2 bg-slate-800 border-slate-700 text-center shadow">
                <img src="{s.get('url')}" class="w-full h-36 object-cover rounded mb-2 border border-slate-600">
                <span class="text-xs font-semibold px-2 py-0.5 rounded bg-red-900/60 text-red-300 uppercase">{s.get('reason')}</span>
                <p class="text-[11px] text-gray-400 mt-1">{s.get('timestamp')}</p>
            </div>
            """

        # Build event timeline rows
        event_rows_html = ""
        for ev in events:
            sev = ev.get("severity", "NORMAL")
            badge_cls = "bg-green-900/50 text-green-300" if sev == "NORMAL" else ("bg-yellow-900/50 text-yellow-300" if sev == "WARNING" else "bg-red-900/50 text-red-300")
            event_rows_html += f"""
            <tr class="border-b border-slate-700/60 hover:bg-slate-800/40">
                <td class="py-2 px-3 text-xs text-gray-400 font-mono">{ev.get('timestamp')}</td>
                <td class="py-2 px-3"><span class="px-2 py-0.5 rounded text-xs font-semibold {badge_cls}">{sev}</span></td>
                <td class="py-2 px-3 text-xs text-slate-200">{ev.get('event_type')}</td>
                <td class="py-2 px-3 text-xs text-slate-300">{ev.get('description')}</td>
                <td class="py-2 px-3 text-xs text-right font-bold text-red-400">{ev.get('total_risk')}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <title>VerifyAI Exam Proctoring Audit Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 p-8 font-sans">
    <div class="max-w-6xl mx-auto space-y-6">
        <!-- Header -->
        <div class="flex justify-between items-center border-b border-slate-800 pb-6">
            <div>
                <h1 class="text-3xl font-extrabold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">VerifyAI Proctoring Audit Report</h1>
                <p class="text-sm text-slate-400">Remote Candidate Examination Security Analysis</p>
            </div>
            <div class="text-right text-xs text-slate-400">
                <p>Generated: <span class="font-semibold text-slate-200">{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></p>
                <p>Status: <span class="text-emerald-400 font-bold">COMPLETED</span></p>
            </div>
        </div>

        <!-- Metric Cards -->
        <div class="grid grid-cols-4 gap-4">
            <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <p class="text-xs text-slate-400">Exam Duration</p>
                <p class="text-2xl font-bold text-slate-100 mt-1">{duration_str}</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <p class="text-xs text-slate-400">Peak Risk Index</p>
                <p class="text-2xl font-bold text-red-400 mt-1">{peak_risk} / 100</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <p class="text-xs text-slate-400">Average Risk Score</p>
                <p class="text-2xl font-bold text-amber-400 mt-1">{avg_risk}</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <p class="text-xs text-slate-400">Total Flagged Incidents</p>
                <p class="text-2xl font-bold text-blue-400 mt-1">{len(events)}</p>
            </div>
        </div>

        <!-- Snapshot Evidence Gallery -->
        {f'''<div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h2 class="text-lg font-semibold text-slate-200 mb-4">Evidence Snapshots</h2>
            <div class="grid grid-cols-4 gap-4">{snapshot_html}</div>
        </div>''' if snapshot_html else ''}

        <!-- Incident Timeline -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h2 class="text-lg font-semibold text-slate-200 mb-4">Incident Log Timeline</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="border-b border-slate-800 text-xs text-slate-400 uppercase">
                            <th class="py-2 px-3">Timestamp</th>
                            <th class="py-2 px-3">Severity</th>
                            <th class="py-2 px-3">Event Type</th>
                            <th class="py-2 px-3">Description</th>
                            <th class="py-2 px-3 text-right">Risk Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {event_rows_html if event_rows_html else '<tr><td colspan="5" class="py-4 text-center text-xs text-slate-500">No violations logged during exam.</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated HTML proctor report: {report_path}")
        return report_path

report_service = ReportService()
