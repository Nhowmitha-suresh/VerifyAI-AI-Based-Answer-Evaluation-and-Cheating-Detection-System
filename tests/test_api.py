"""
Unit Tests for FastAPI REST API Endpoints.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "version" in data

def test_status_endpoint():
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "session_active" in data
    assert "current_risk" in data

def test_risk_endpoint():
    response = client.get("/risk")
    assert response.status_code == 200
    data = response.json()
    assert "current_risk" in data
    assert "severity" in data

def test_events_endpoint():
    response = client.get("/events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data

def test_snapshots_endpoint():
    response = client.get("/snapshots")
    assert response.status_code == 200
    data = response.json()
    assert "snapshots" in data

def test_reset_risk_action():
    response = client.post("/reset-risk")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
