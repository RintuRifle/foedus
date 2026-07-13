"""
Foedus — Evaluation Schemas
"""

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

class EvalTriggerResponse(BaseModel):
    job_id: uuid.UUID
    status: str = "queued"
    message: str = "Evaluation job queued successfully"

class EvalProgressResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    progress_pct: int
    current_agent: Optional[str]
    current_message: Optional[str]
    started_at: Optional[datetime]
    duration_seconds: Optional[float] = None

    model_config = {"from_attributes": True}

class ComplianceItemResponse(BaseModel):
    criterion: str
    category: Optional[str]
    required_value: Optional[str]
    user_value: Optional[str]
    status: Literal["met", "partial", "missing"]
    source_quote: Optional[str]
    notes: Optional[str]

    model_config = {"from_attributes": True}

class EvalReportResponse(BaseModel):
    job_id: uuid.UUID
    tender_title: str
    status: str
    match_score: Optional[float] = None
    match_reasons: Optional[List[str]] = None
    eligibility_status: Optional[str] = None
    compliance_matrix: List[ComplianceItemResponse] = []
    win_probability: Optional[float] = None
    risk_factors: Optional[List[str]] = None
    competition_level: Optional[str] = None
    duration_seconds: Optional[float] = None
    completed_at: Optional[datetime] = None

class WebSocketProgressEvent(BaseModel):
    """Event sent over WebSocket during evaluation."""
    job_id: str
    agent: str
    progress: int = Field(ge=0, le=100)
    message: str
    status: str
    timestamp: datetime
