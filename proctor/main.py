"""
Main Proctoring Application Engine & Thread Orchestrator.
Integrates Multi-Modal Telemetry, Explainable AI Behavioral Engine, Circular Video Buffer & Gaze Heatmaps.
"""

import sys
import time
import math
import cv2
import ctypes
import collections
import numpy as np

from .utils import SilenceFD, calculate_ear

# Silence MediaPipe C++ graph dumps during import and solution creation
with SilenceFD():
    import mediapipe as mp

from .config import (
    CAM_W, CAM_H, PROCESS_EVERY_N, ENABLE_HANDS, ENABLE_OBJECT_DETECTION, ENABLE_AUDIO,
    ALARM_MEDIUM, ALARM_HIGH, HAND_FACE_DIST_RATIO, HAND_SUSTAIN,
    EAR_CLOSED_THRESH, EAR_CLOSED_SUSTAIN, MOUTH_OPEN_THRESHOLD, VAD_WINDOW, MOUTH_TOP_BOTTOM,
    WEIGHT_PHONE_DETECTED, WEIGHT_WINDOW_SWITCH, WEIGHT_OFFSCREEN, WEIGHT_HEADTURN,
    WEIGHT_FULLTURN, WEIGHT_HAND_NEAR, WEIGHT_MULTIFACE, WEIGHT_OCCLUSION,
    WEIGHT_OTHERVOICE, WEIGHT_EYES_CLOSED
)
from .camera import CameraManager
from .gaze import GazeTracker
from .headpose import HeadPoseEstimator
from .phone_detector import ObjectDetector
from .audio import AudioMonitor, start_alert, stop_alerts
from .logger import events, logger, push_event, log_event, current_score, save_snapshot
from .hud import draw_hud_header, draw_risk_gauge, draw_telemetry_panel, draw_event_feed
from .behavior_engine import BehavioralRiskEngine
from .timeline import IncidentRecorder
from .heatmap import GazeHeatmapTracker
from .identity import IdentityVerifier
from .analytics import SessionAnalytics
from .report import generate_html_report


import urllib.request
import json
import threading

def sync_telemetry_to_backend(payload):
    def _post():
        try:
            req = urllib.request.Request(
                "http://localhost:8000/api/telemetry/update",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=0.5)
        except Exception:
            pass
    threading.Thread(target=_post, daemon=True).start()


def get_active_window_title():
    if sys.platform == "win32":
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value or "Unknown Window"
        except Exception as e:
            logger.debug(f"Failed to fetch active window title: {e}")
            return "Unknown Window"
    return "Proctoring Window"


def main():
    print("[PASS] STEP 1 - Starting AI Proctoring Application Engine...", flush=True)
    logger.info("[STARTUP] [1/10] Starting AI Proctoring Application Engine...")
    
    try:
        print("[PASS] STEP 2 - Initializing MediaPipe FaceMesh & Hands Solutions...", flush=True)
        logger.info("[STARTUP] [2/10] Initializing MediaPipe FaceMesh & Hands Solutions...")
        with SilenceFD():
            face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=2,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            hands = mp.solutions.hands.Hands(
                max_num_hands=2,
                min_detection_confidence=0.5
            ) if ENABLE_HANDS else None

            # Warmup first frame inside SilenceFD to capture lazy C++ graph compilation dumps!
            dummy_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
            face_mesh.process(dummy_rgb)
            if hands:
                hands.process(dummy_rgb)

        print("[PASS] STEP 2 - MediaPipe Solutions Initialized & Warmed Up", flush=True)
        logger.info("[STARTUP] [2/10] MediaPipe Solutions initialized & warmed up cleanly.")

        print("[PASS] STEP 3 - Initializing CameraManager...", flush=True)
        logger.info("[STARTUP] [3/10] Initializing CameraManager...")
        camera = CameraManager(width=CAM_W, height=CAM_H)
        camera.start()
        print("[PASS] STEP 3 - CameraManager Started Successfully", flush=True)
        logger.info("[STARTUP] [3/10] CameraManager started successfully.")

        print("[PASS] STEP 4 - Initializing GazeTracker & Heatmap Engine...", flush=True)
        logger.info("[STARTUP] [4/10] Initializing GazeTracker & Heatmap Engine...")
        gaze_tracker = GazeTracker()
        heatmap_tracker = GazeHeatmapTracker()

        print("[PASS] STEP 5 - Initializing HeadPoseEstimator & Identity Verifier...", flush=True)
        logger.info("[STARTUP] [5/10] Initializing HeadPoseEstimator & Identity Verifier...")
        head_pose_estimator = HeadPoseEstimator()
        identity_verifier = IdentityVerifier()

        print("[PASS] STEP 6 - Initializing ObjectDetector...", flush=True)
        logger.info("[STARTUP] [6/10] Initializing ObjectDetector...")
        object_detector = None
        if ENABLE_OBJECT_DETECTION:
            try:
                object_detector = ObjectDetector()
            except Exception as e:
                logger.warning(f"ObjectDetector initialization failed: {e}. Subsystem disabled.")

        print("[PASS] STEP 7 - Initializing AudioMonitor...", flush=True)
        logger.info("[STARTUP] [7/10] Initializing AudioMonitor...")
        audio_mon = None
        if ENABLE_AUDIO:
            try:
                audio_mon = AudioMonitor()
                audio_mon.start()
            except Exception as e:
                logger.warning(f"AudioMonitor initialization failed: {e}. Subsystem disabled.")

        print("[PASS] STEP 8 - Initializing Behavioral AI & Incident Buffer...", flush=True)
        logger.info("[STARTUP] [8/10] Initializing Behavioral AI & Incident Buffer...")
        behavior_engine = BehavioralRiskEngine()
        incident_recorder = IncidentRecorder()
        session_analytics = SessionAnalytics()

        initial_window = get_active_window_title()

        # Calibration Phase
        print("[PASS] STEP 9 - Calibration Starting...", flush=True)
        logger.info("[STARTUP] [9/10] Calibration starting...")
        calib_samples = []
        calib_start = time.time()
        while time.time() - calib_start < 2.5:
            ret, frame = camera.read()
            if not ret or frame is None:
                time.sleep(0.02)
                continue
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)
            if res.multi_face_landmarks:
                lm = np.array([(int(p.x * w), int(p.y * h)) for p in res.multi_face_landmarks[0].landmark])
                try:
                    g_res = gaze_tracker.process(lm, time.time())
                    calib_samples.append((g_res["dx"], g_res["dy"]))
                    identity_verifier.register_baseline(lm)
                except Exception as e:
                    logger.debug(f"Calibration gaze processing exception: {e}")
            cv2.putText(frame, "CALIBRATING GAZE BASELINE... LOOK AT CENTER", (w // 2 - 260, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
            try:
                cv2.imshow("Proctoring System", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
            except Exception as e:
                logger.warning(f"Calibration window display error: {e}")

        if calib_samples:
            calib_center = np.mean(calib_samples, axis=0)
            gaze_tracker.calibrate((0.5 + calib_center[0], 0.5 + calib_center[1]))
        print("[PASS] STEP 9 - Calibration & Identity Registration Completed", flush=True)
        logger.info("[STARTUP] [9/10] Baseline calibration & identity registration completed.")

        frame_idx = 0
        start_time = time.time()
        last_frame_time = time.time()
        fps = 30.0

        hand_buf = collections.deque()
        occ_buf = collections.deque()
        mf_buf = collections.deque()
        ear_buf = collections.deque()

        try:
            cv2.namedWindow("Proctoring System", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Proctoring System", 1280, 720)
        except Exception as e:
            logger.warning(f"Could not resize OpenCV window: {e}")

        last_high_snapshot = 0
        last_phone_snapshot = 0
        last_incident_trigger = 0

        print("[PASS] STEP 10 - Entering Main Detection Loop (OpenCV Window Active)", flush=True)
        logger.info("[STARTUP] [10/10] Entering main detection loop...")

        while True:
            ret, frame = camera.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            h, w = frame.shape[:2]
            frame_idx += 1
            now = time.time()

            # Push frame into circular video recorder
            incident_recorder.push_frame(frame, now)

            dt = now - last_frame_time
            last_frame_time = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = None
            hands_res = None
            detections = []

            if (frame_idx % PROCESS_EVERY_N) == 0:
                results = face_mesh.process(rgb)
                if ENABLE_HANDS and hands:
                    hands_res = hands.process(rgb)
                if object_detector:
                    detections = object_detector.detect_objects(frame)

            offscreen_flag = headturn_flag = fullturn_flag = handnear_flag = False
            multiface_flag = occlusion_flag = othervoice_flag = eyes_closed_flag = False
            phone_flag = window_switch_flag = rapid_scan_flag = lap_glance_flag = False

            gaze_str, head_str, face_str, hand_str, audio_str, ear_str = "CENTER", "NORMAL", "1 Face", "CLEAR", "QUIET", "ACTIVE"
            phone_str, window_str = "CLEAR", "FOCUSED"
            phone_conf = 0.0

            # 1. MOBILE PHONE & FORBIDDEN OBJECT DETECTION
            if detections:
                for obj in detections:
                    label = obj["label"]
                    conf = obj["confidence"]
                    (bx, by, bw, bh) = obj["box"]
                    
                    if label in ["cell phone", "mobile phone"]:
                        phone_flag = True
                        phone_conf = max(phone_conf, conf)
                        phone_str = f"PHONE ({int(conf*100)}%)"
                        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 0, 255), 3)
                        cv2.putText(frame, f"MOBILE PHONE {int(conf*100)}%", (bx, max(20, by - 8)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
                        
                        if now - last_phone_snapshot > 3.0:
                            save_snapshot(frame, reason="mobile_phone")
                            last_phone_snapshot = now

            # 2. ACTIVE WINDOW PROCTORING
            curr_window = get_active_window_title()
            if curr_window and curr_window != initial_window and "Proctoring System" not in curr_window:
                window_switch_flag = True
                window_str = "UNFOCUSED"

            # 3. FACEMESH & TELEMETRY
            if results and results.multi_face_landmarks:
                nfaces = len(results.multi_face_landmarks)
                face_str = f"{nfaces} Faces"
                if nfaces > 1:
                    mf_buf.append(now)
                    if now - mf_buf[0] > 0.8:
                        multiface_flag = True
                else:
                    mf_buf.clear()

                lm = np.array([(int(p.x * w), int(p.y * h)) for p in results.multi_face_landmarks[0].landmark])

                # Identity Verification Check
                id_res = identity_verifier.verify(lm)
                if not id_res["verified"]:
                    face_str = "UNVERIFIED PERSON"

                # Gaze Analytics & Heatmap
                g_res = gaze_tracker.process(lm, now)
                gaze_str = g_res["gaze_direction"]
                offscreen_flag = g_res["offscreen"]
                rapid_scan_flag = g_res["rapid_scan"]

                heatmap_tracker.push_gaze_point(0.5 + g_res["dx"], 0.5 + g_res["dy"])

                if g_res["Lc"] != (0, 0):
                    cv2.circle(frame, g_res["Lc"], 3, (0, 255, 255), -1)
                    cv2.circle(frame, g_res["Rc"], 3, (0, 255, 255), -1)

                # Head Pose Analytics
                hp_res = head_pose_estimator.process(lm, w, h, now, gaze_dir=gaze_str, dy=g_res["dy"])
                head_str = hp_res["head_status"]
                headturn_flag = hp_res["headturn"]
                fullturn_flag = hp_res["fullturn"]
                lap_glance_flag = hp_res["lap_glance"]

                if hp_res["axis_pts"]:
                    cv2.line(frame, hp_res["axis_pts"][0], hp_res["axis_pts"][1], (0, 165, 255), 2)

                # Drowsiness / Eye Aspect Ratio
                ear = calculate_ear(lm)
                if ear < EAR_CLOSED_THRESH:
                    ear_buf.append(now)
                    ear_str = "EYES CLOSED"
                else:
                    ear_buf.clear()
                    ear_str = "ACTIVE"
                if ear_buf and (now - ear_buf[0]) > EAR_CLOSED_SUSTAIN:
                    eyes_closed_flag = True
            else:
                occ_buf.append(now)
                face_str = "NO FACE"
                if occ_buf and (now - occ_buf[0]) > 0.8:
                    occlusion_flag = True

            # Hands Near Face
            if ENABLE_HANDS and hands_res and hands_res.multi_hand_landmarks and results and results.multi_face_landmarks:
                lm = np.array([(int(p.x * w), int(p.y * h)) for p in results.multi_face_landmarks[0].landmark])
                fx0, fy0 = lm[:, 0].min(), lm[:, 1].min()
                fx1, fy1 = lm[:, 0].max(), lm[:, 1].max()
                face_center = np.array([(fx0 + fx1) / 2.0, (fy0 + fy1) / 2.0])
                face_diag = math.hypot(fx1 - fx0, fy1 - fy0)

                for hand in hands_res.multi_hand_landmarks:
                    pts = np.array([(int(p.x * w), int(p.y * h)) for p in hand.landmark])
                    hcx, hcy = pts[:, 0].mean(), pts[:, 1].mean()
                    cv2.circle(frame, (int(hcx), int(hcy)), 5, (255, 0, 200), -1)
                    d = math.hypot(hcx - face_center[0], hcy - face_center[1])
                    if d < HAND_FACE_DIST_RATIO * face_diag:
                        hand_buf.append(now)
                        hand_str = "HAND NEAR FACE"
                if hand_buf and (now - hand_buf[0]) > HAND_SUSTAIN:
                    handnear_flag = True
            else:
                hand_buf.clear()

            # Audio VAD Correlation
            if ENABLE_AUDIO and audio_mon:
                audio_act = audio_mon.recent_audio_activity(window_sec=VAD_WINDOW)
                mouth_open = 0.0
                if results and results.multi_face_landmarks:
                    lm = np.array([(int(p.x * w), int(p.y * h)) for p in results.multi_face_landmarks[0].landmark])
                    top = lm[MOUTH_TOP_BOTTOM[0]]
                    bot = lm[MOUTH_TOP_BOTTOM[1]]
                    nose, chin = lm[1], lm[152]
                    mouth_open = float(np.linalg.norm(top - bot) / max(1.0, np.linalg.norm(nose - chin)))

                if audio_act:
                    audio_str = "VOICE SPEECH" if mouth_open >= MOUTH_OPEN_THRESHOLD else "SUSPICIOUS VOICE"
                    if mouth_open < MOUTH_OPEN_THRESHOLD:
                        othervoice_flag = True
                else:
                    audio_str = "QUIET"

            telemetry_flags = {
                "phone_status": phone_str, "phone_detected": phone_flag, "phone_confidence": float(phone_conf),
                "window_status": window_str, "window_switched": window_switch_flag,
                "gaze_status": gaze_str, "offscreen": offscreen_flag, "rapid_scan": rapid_scan_flag,
                "head_status": head_str, "headturn": headturn_flag or fullturn_flag, "lap_glance": lap_glance_flag,
                "face_status": face_str, "multiface": multiface_flag, "occlusion": occlusion_flag,
                "hand_status": hand_str, "handnear": handnear_flag,
                "audio_status": audio_str, "othervoice": othervoice_flag,
                "ear_status": ear_str, "eyes_closed": eyes_closed_flag
            }

            # 4. Behavioral Risk AI Engine Evaluation
            risk_eval = behavior_engine.evaluate_telemetry(telemetry_flags, now)
            score = risk_eval["risk_score"]
            explanation = risk_eval["explanation"]

            sync_telemetry_to_backend({
                **telemetry_flags,
                "risk_score": score,
                "severity": risk_eval["severity"],
                "explanation": explanation
            })

            # Trigger Incident Video Recording on High Risk
            if score >= ALARM_HIGH and (now - last_incident_trigger > 12.0):
                incident_recorder.trigger_incident("High Risk Violation", score, explanation)
                save_snapshot(frame, reason="high_risk")
                last_incident_trigger = now

            if score >= ALARM_HIGH or phone_flag:
                start_alert("high")
                status_text = "CRITICAL RISK - ALARM"
            elif score >= ALARM_MEDIUM:
                start_alert("medium")
                status_text = "WARNING - SUSPICIOUS"
            else:
                stop_alerts()
                status_text = "MONITORING - NORMAL"

            elapsed = now - start_time
            draw_hud_header(frame, fps, elapsed, score, status_text, curr_window)
            draw_risk_gauge(frame, score)
            
            draw_telemetry_panel(frame, telemetry_flags)
            draw_event_feed(frame, events)

            global current_processed_frame
            current_processed_frame = frame.copy()

            try:
                cv2.imshow("Proctoring System", frame)
                k = cv2.waitKey(1) & 0xFF
                if k == 27 or k == ord('q') or k == ord('Q'):
                    logger.info("User requested exit.")
                    break
                elif k == ord('c') or k == ord('C'):
                    gaze_tracker.calibrate((0.5, 0.5))
                    logger.info("Recalibrated gaze baseline.")
                elif k == ord('r') or k == ord('R'):
                    events.clear()
                    behavior_engine.cumulative_score = 0.0
                    logger.info("Reset risk score.")
                elif k == ord('s') or k == ord('S'):
                    save_snapshot(frame, reason="manual")
            except Exception as e:
                logger.warning(f"Main loop display exception: {e}")

    except Exception as e:
        logger.exception("[CRITICAL STARTUP FAILURE] Execution halted due to unhandled exception:")
        raise e
    finally:
        logger.info("Cleaning up proctoring subsystems...")
        if 'audio_mon' in locals() and audio_mon:
            audio_mon.stop()
        if 'camera' in locals() and camera:
            camera.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        if 'face_mesh' in locals() and face_mesh:
            face_mesh.close()
        if 'hands' in locals() and hands:
            hands.close()
        
        # Export Gaze Heatmap & HTML Session Audit Report
        try:
            heatmap_tracker.generate_heatmap_overlay(np.zeros((720, 1280, 3), dtype=np.uint8))
            gaze_analytics = heatmap_tracker.compute_analytics()
            incidents = incident_recorder.get_incidents()
            analytics_summary = session_analytics.get_summary(gaze_analytics, incidents)
            generate_html_report(incident_logs=incidents, analytics_summary=analytics_summary)
        except Exception as e:
            logger.error(f"Error during report export: {e}")

        logger.info("Proctoring session exited cleanly.")


if __name__ == "__main__":
    main()
