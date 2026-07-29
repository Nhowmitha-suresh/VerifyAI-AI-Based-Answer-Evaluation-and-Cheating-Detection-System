"""
Audio Monitor, Speech Synthesis & Collusion Analytics Module.
"""

import sys
import time
import threading
import collections
import numpy as np
from .config import (
    MOUTH_OPEN_THRESHOLD, AUDIO_RMS_THRESHOLD, VAD_WINDOW,
    TTS_RATE, AUDIO_RATE, AUDIO_CHANNELS, AUDIO_BLOCK_MS
)
from .logger import logger

try:
    import sounddevice as sd
except Exception as e:
    logger.info(f"[AUDIO INFO] PyAudio / sounddevice not available ({e}). Microphone VAD will be disabled.")
    sd = None

try:
    import webrtcvad
    HAS_VAD = True
except Exception as e:
    logger.info(f"[AUDIO INFO] WebRTC VAD not available ({e}). Falling back to RMS energy VAD.")
    HAS_VAD = False

if sys.platform == "win32":
    try:
        import winsound
    except Exception:
        winsound = None
else:
    winsound = None

try:
    import pyttsx3
    tts_engine = pyttsx3.init()
    tts_engine.setProperty("rate", TTS_RATE)
except Exception as e:
    logger.info(f"[AUDIO INFO] PyTTSx3 synthesis unavailable ({e}). Voice alerts disabled.")
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
            except Exception as e:
                logger.debug(f"TTS Engine execution error: {e}")
    threading.Thread(target=_run, daemon=True).start()

def beep(freq=1000, duration=300):
    if winsound and sys.platform == "win32":
        try:
            winsound.Beep(freq, duration)
        except Exception as e:
            logger.debug(f"Winsound beep error: {e}")

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
    elif mode in ["high", "danger", "phone"]:
        def loop():
            while True:
                with _alarm_lock:
                    if _stop_alarm:
                        break
                beep(1400, 250)
                time.sleep(0.08)
                with _alarm_lock:
                    if _stop_alarm:
                        break
                beep(1050, 250)
                time.sleep(0.10)
        threading.Thread(target=loop, daemon=True).start()
        if mode == "phone":
            speak_async("DANGER ALERT! CELL PHONE DETECTED! PROCTORING VIOLATION!")
        else:
            speak_async("DANGER ALERT! HIGH RISK PROCTORING VIOLATION THRESHOLD EXCEEDED!")

def stop_alerts():
    global _alarm_mode, _stop_alarm
    with _alarm_lock:
        _stop_alarm = True
        _alarm_mode = None


class AudioMonitor:
    def __init__(self, rate=AUDIO_RATE, channels=AUDIO_CHANNELS, block_ms=AUDIO_BLOCK_MS):
        self.rate = rate
        self.channels = channels
        self.block_ms = block_ms
        self.buffer = collections.deque(maxlen=int(2000 / block_ms))
        self.vad = None
        if HAS_VAD:
            try:
                self.vad = webrtcvad.Vad(2)
            except Exception as e:
                logger.warning(f"WebRTC VAD initialization error: {e}")
                self.vad = None
        self.stream = None
        self.running = False

    def start(self):
        if sd is None:
            logger.info("Sounddevice microphone stream skipped (library not installed).")
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
            logger.info("Microphone audio stream started successfully.")
        except Exception as e:
            logger.warning(f"[AUDIO WARN] Microphone capture stream error: {e}. Audio VAD disabled.")
            self.running = False

    def _callback(self, indata, frames, time_info, status):
        if indata is None:
            return
        try:
            pcm16 = (indata[:, 0] * 32767).astype(np.int16).tobytes()
            self.buffer.append(pcm16)
        except Exception as e:
            logger.debug(f"Audio stream callback exception: {e}")

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.debug(f"Error stopping microphone stream: {e}")
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
            except Exception as e:
                logger.debug(f"Audio RMS calculation exception: {e}")
                return False
