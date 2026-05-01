import requests
import base64
import io
import wave
import os

BASE = 'http://127.0.0.1:8000'

def start_session():
    r = requests.post(BASE + '/session/start')
    r.raise_for_status()
    return r.json().get('session_id')

def send_flagged_frame(session_id):
    # 1x1 white JPEG (tiny)
    jpg_b64 = '/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxISEhUSEhIVFhUVFRUVFRUVFRUVFRUWFhUVFRUYHSggGBolGxUVITEhJSkrLi4uFx8zODMtNygtLisBCgoKDg0OGxAQGy0lICYtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAKABJAMBIgACEQEDEQH/xAAbAAEAAgMBAQAAAAAAAAAAAAAABQYBAwQCB//EADkQAAIBAgQDBgQFBQAAAAAAAAECAwQRAAUSIRMxQVFhBhMicYGRI0KhscHR8PFCUuH/xAAYAQEBAQEBAAAAAAAAAAAAAAAAAgEDBP/EACERAQEBAQACAwEAAAAAAAAAAAABEQISITFRBBNhcYH/2gAMAwEAAhEDEQA/AL9QCEAhACEAhACEAhACEAhACEAhACEAhACEAhACEAhACEAhACEAhACEAhACEAhACEAhACEAhACEAhACEAhACED//2Q=='
    data = base64.b64decode(jpg_b64)
    files = {'file': ('frame.jpg', io.BytesIO(data), 'image/jpeg')}
    reasons = {'reasons': '[]', 'integrity': '50'}
    url = BASE + f'/flagged-frame?session={session_id}'
    r = requests.post(url, files=files, data=reasons)
    print('flagged-frame status', r.status_code, r.text)
    r.raise_for_status()

def send_audio_and_transcribe(session_id):
    # generate 1s silence WAV
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        samples = (b'\x00\x00' * 16000)
        wf.writeframes(samples)
    buf.seek(0)
    files = {'file': ('audio.wav', buf, 'audio/wav')}
    url = BASE + f'/audio/transcribe?session={session_id}'
    r = requests.post(url, files=files)
    print('transcribe status', r.status_code)
    try:
        print('transcribe json:', r.json())
    except Exception:
        print('transcribe text:', r.text[:200])
    return r

def auth_eval(transcript, duration):
    url = BASE + '/auth/evaluate'
    r = requests.post(url, json={'transcript': transcript, 'duration_seconds': duration})
    print('auth eval status', r.status_code, r.text)
    r.raise_for_status()
    return r.json()

def list_flagged():
    path = os.path.join(os.getcwd(), 'flagged_frames')
    if not os.path.isdir(path):
        print('no flagged_frames dir yet')
        return []
    files = sorted(os.listdir(path))
    print('flagged frames:', files[:10])
    return files

def main():
    sid = start_session()
    print('session', sid)
    send_flagged_frame(sid)
    list_flagged()
    r = send_audio_and_transcribe(sid)
    if r.status_code == 200:
        j = r.json()
        auth = auth_eval(j.get('transcript',''), 1.0)
        print('auth result', auth)
    else:
        print('No server ASR available; simulate client-side transcript and eval')
        auth = auth_eval('This is a test transcript generated locally.', 1.0)
        print('auth result', auth)

if __name__ == '__main__':
    main()
