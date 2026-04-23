"""Simple smoke tests for verifAI backend.
Run after backend is running:

    python scripts/smoke_test.py

Requires: `requests` (install into your backend venv)
"""
import requests
import sys

BASE = "http://127.0.0.1:8000"


def ok(msg):
    print("[OK]", msg)


def fail(msg):
    print("[FAIL]", msg)


def test_health():
    try:
        r = requests.get(BASE + "/health", timeout=3)
        if r.status_code == 200:
            ok(f"health -> {r.json()}")
        else:
            fail(f"health returned {r.status_code}")
    except Exception as e:
        fail(f"health request error: {e}")


def test_nlp():
    payload = {"question": "What is TCP?", "answer": "TCP is connection oriented and reliable.", "keywords": ["connection", "reliable"]}
    try:
        r = requests.post(BASE + "/nlp/score", json=payload, timeout=5)
        if r.status_code == 200:
            print("/nlp/score ->", r.json())
        else:
            fail(f"nlp score returned {r.status_code}")
    except Exception as e:
        fail(f"nlp request error: {e}")


if __name__ == '__main__':
    print('Running verifAI smoke tests against', BASE)
    test_health()
    test_nlp()
    print('Done')
