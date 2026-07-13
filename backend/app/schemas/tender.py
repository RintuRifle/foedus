"""
Foedus — Tender Schemas
"""

import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

class TenderResponse(BaseModel):
    id: uuid.UUID
    external_id: Optional[str]
    source: str
    title: str
    description: Optional[str]
    sector: Optional[List[str]]
    state: Optional[str]
    department: Optional[str]
    organization: Optional[str]
    value_lakh: Optional[float]
    emd_amount: Optional[float]
    tender_fee: Optional[float]
    submission_date: Optional[date]
    opening_date: Optional[date]
    published_date: Optional[date]
    pdf_url: Optional[str]
    status: str
    days_remaining: Optional[int] = None
    scraped_at: datetime

    model_config = {"from_attributes": True}

class TenderFeedItem(BaseModel):
    """Tender with match score for personalized feed."""
    tender: TenderResponse
    match_score: float = Field(ge=0, le=1)
    match_reasons: Optional[List[str]] = None
    is_saved: bool = False
    is_seen: bool = False

class TenderSearchParams(BaseModel):
    q: Optional[str] = None
    state: Optional[str] = None
    sector: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    source: Optional[str] = None
    status: str = "active"
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)

class TenderListResponse(BaseModel):
    items: List[TenderFeedItem]
    total: int
    page: int
    per_page: int
    has_next: bool
