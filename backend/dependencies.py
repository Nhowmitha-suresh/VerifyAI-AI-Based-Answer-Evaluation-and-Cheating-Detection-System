"""
FastAPI Dependency Injection helper module.
"""

from backend.core.app_state import app_state
from backend.services.webcam_service import webcam_service
from backend.services.risk_service import risk_engine

def get_app_state():
    return app_state

def get_webcam_service():
    return webcam_service

def get_risk_engine():
    return risk_engine
