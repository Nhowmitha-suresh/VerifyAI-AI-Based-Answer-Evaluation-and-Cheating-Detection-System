"""Generate a short WAV, POST to backend /audio/transcribe, and print response."""
import wave
import math
import struct
import tempfile
import requests
import os

BASE = "http://127.0.0.1:8000"

def make_sine_wav(path, duration=1.0, freq=440.0, rate=16000):
    samples = int(duration * rate)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        for i in range(samples):
            t = i / rate
            val = int(32767 * 0.2 * math.sin(2 * math.pi * freq * t))
            wf.writeframes(struct.pack('<h', val))

def main():
    fd, path = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        make_sine_wav(path)
        print('WAV created at', path)
        with open(path, 'rb') as fh:
            files = {'file': ('test.wav', fh, 'audio/wav')}
            try:
                # model downloads or transcription may take long; allow up to 10 minutes
                r = requests.post(BASE + '/audio/transcribe', files=files, timeout=600)
                print('status', r.status_code)
                try:
                    print('json ->', r.json())
                except Exception:
                    print('response text ->', r.text[:1000])
            except Exception as e:
                print('request error', e)
    finally:
        try: os.remove(path)
        except Exception: pass

if __name__ == '__main__':
    main()
