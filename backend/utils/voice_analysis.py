"""Simple voice analysis utilities for backend (transcript-based).
These functions are intentionally lightweight and deterministic.
"""
import re

FILLERS = [r'\bum\b', r'\buh\b', r"\blike\b", r"\byou know\b", r"\bso\b", r"\bactually\b"]

def analyze_transcript(transcript: str, duration_seconds: float = 0.0):
    text = (transcript or '').lower()
    words = re.findall(r"\w+'?\w*|\w+", text)
    word_count = len(words)

    filler_count = 0
    for pat in FILLERS:
        filler_count += len(re.findall(pat, text))

    filler_ratio = (filler_count / word_count) if word_count else 0.0
    speaking_speed = (word_count / max(0.1, duration_seconds)) if duration_seconds else 0.0

    confidence_score = max(0.0, min(1.0, (1.0 - filler_ratio) * min(1.0, word_count / 50.0)))

    return {
        'filler_ratio': round(filler_ratio, 3),
        'speaking_speed': round(speaking_speed, 3),
        'confidence_score': round(confidence_score, 3)
    }
