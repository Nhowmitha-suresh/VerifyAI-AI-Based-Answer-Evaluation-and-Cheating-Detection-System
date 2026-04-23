"""Create a simple test image and POST to backend /detect-face endpoint."""
import cv2
import numpy as np
import tempfile
import requests
import os

BASE = "http://127.0.0.1:8000"


def make_test_image(path):
    img = np.full((480, 640, 3), 255, dtype=np.uint8)
    # draw a dark circle roughly face-shaped
    cv2.circle(img, (320, 240), 80, (50, 50, 50), -1)
    cv2.imwrite(path, img)


def main():
    fd, path = tempfile.mkstemp(suffix='.jpg')
    os.close(fd)
    try:
        make_test_image(path)
        print('Test image at', path)
        with open(path, 'rb') as fh:
            files = {'file': ('test.jpg', fh, 'image/jpeg')}
            try:
                r = requests.post(BASE + '/detect-face', files=files, timeout=10)
                print('status', r.status_code)
                try:
                    print('json ->', r.json())
                except Exception:
                    print('text ->', r.text)
            except Exception as e:
                print('request error', e)
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


if __name__ == '__main__':
    main()
