"""
Pydantic Data Models for Incident Events.
"""

from pydantic import BaseModel
from typing import Optional

class ProctorEvent(BaseModel):
    id: str
    timestamp: str
    event_type: str
    severity: str
    description: str
    risk_contribution: float
    total_risk: float
    snapshot_url: Optional[str] = None
