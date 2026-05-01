"""Minimal face detection helpers using OpenCV.
These are lightweight helpers used by backend processing pipelines.
"""
import cv2
import numpy as np
import os

def detect_faces_from_image(path):
    """
    Load image from path and run OpenCV Haar cascade face detection.
    Returns: dict with face_count, bboxes (x,y,w,h)
    """
    if not os.path.exists(path):
        return { 'face_count': 0, 'bboxes': [] }
    img = cv2.imread(path)
    if img is None:
        return { 'face_count': 0, 'bboxes': [] }
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Use the default haarcascade included with opencv package if available
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    if not os.path.exists(cascade_path):
        return { 'face_count': 0, 'bboxes': [] }
    face_cascade = cv2.CascadeClassifier(cascade_path)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))
    bboxes = []
    for (x,y,w,h) in faces:
        bboxes.append([int(x), int(y), int(w), int(h)])
    return { 'face_count': len(bboxes), 'bboxes': bboxes }
