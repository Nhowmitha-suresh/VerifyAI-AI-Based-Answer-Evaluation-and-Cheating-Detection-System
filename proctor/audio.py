"""
Audio Monitor, Speech Synthesis & Collusion Analytics Module.
"""

import sys
import time
import threading
import collections
import numpy as np
from .config import MOUTH_OPEN_THRESHOLD, AUDIO_RMS_THRESHOLD, VAD_WINDOW

try:
    import sounddevice as sd
except Exception:
    sd = None

try:
    import webrtcvad
    HAS_VAD = True
except Exception:
    HAS_VAD = False

if sys.platform == "win32":
    import winsound

try:
    import pyttsx3
    tts_engine = pyttsx3.init()
    tts_engine.setProperty("rate", 155)
except Exception:
    tts_engine = None

_alarm_lock = threading.Lock()
_alarm_mode = None
_stop_alarm = False
_last_speech_time = 0

def speak_async(text):
    global _last_speech_time
    if time.time() - _last_speech_time < 3.0:
        return
    _last_speech_time = time.time()
    def _run():
        if tts_engine:
            try:
                tts_engine.say(text)
                tts_engine.runAndWait()
            except Exception:
                pass
    threading.Thread(target=_run, daemon=True).start()

def beep(freq=1000, duration=300):
    if sys.platform == "win32":
        try:
            winsound.Beep(freq, duration)
        except Exception:
            pass

def start_alert(mode):
    global _alarm_mode, _stop_alarm
    with _alarm_lock:
        if _alarm_mode == mode:
            return
        _alarm_mode = mode
        _stop_alarm = False

    if mode == "low":
        threading.Thread(target=lambda: beep(900, 200), daemon=True).start()
        speak_async("Please focus on the screen.")
    elif mode == "medium":
        threading.Thread(target=lambda: (beep(1000, 300), time.sleep(0.1), beep(1000, 300)), daemon=True).start()
        speak_async("Warning: Suspicious behavior detected.")
    elif mode == "high":
        def loop():
            while True:
                with _alarm_lock:
                    if _stop_alarm:
                        break
                beep(1300, 400)
                time.sleep(0.15)
        threading.Thread(target=loop, daemon=True).start()
        speak_async("High risk alert: Proctoring violation threshold exceeded!")

def stop_alerts():
    global _alarm_mode, _stop_alarm
    with _alarm_lock:
        _stop_alarm = True
        _alarm_mode = None


class AudioMonitor:
    def __init__(self, rate=16000, channels=1, block_ms=200):
        self.rate = rate
        self.channels = channels
        self.block_ms = block_ms
        self.buffer = collections.deque(maxlen=int(2000 / block_ms))
        self.vad = None
        if HAS_VAD:
            try:
                self.vad = webrtcvad.Vad(2)
            except Exception:
                self.vad = None
        self.stream = None
        self.running = False

    def start(self):
        if sd is None:
            return
        try:
            self.running = True
            self.stream = sd.InputStream(
                channels=self.channels,
                samplerate=self.rate,
                blocksize=int(self.rate * self.block_ms / 1000),
                callback=self._callback
            )
            self.stream.start()
        except Exception as e:
            print("[AUDIO WARN] Microphone capture stream error:", e)

    def _callback(self, indata, frames, time_info, status):
        if indata is None:
            return
        pcm16 = (indata[:, 0] * 32767).astype(np.int16).tobytes()
        self.buffer.append(pcm16)

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
        self.running = False

    def recent_audio_activity(self, window_sec=0.6):
        if self.vad is not None:
            cnt, total = 0, 0
            num_blocks = int(window_sec * 1000 / self.block_ms)
            for pcm in list(self.buffer)[-num_blocks:]:
                total += 1
                try:
                    if self.vad.is_speech(pcm, sample_rate=self.rate):
                        cnt += 1
                except Exception:
                    pass
            return cnt > 0 and (cnt / max(1, total)) > 0.15
        else:
            if not self.buffer:
                return False
            num_blocks = int(window_sec * 1000 / self.block_ms)
            pcm = b"".join(list(self.buffer)[-num_blocks:])
            try:
                arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32767.0
                rms = np.sqrt(np.mean(arr * arr)) if arr.size else 0.0
                return rms > AUDIO_RMS_THRESHOLD
            except Exception:
                return False
