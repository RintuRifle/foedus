"""
TenderAI — Company & Document Schemas
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

class CompanyCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    sector: Optional[List[str]] = None
    turnover_lakh: Optional[float] = None
    emp_count: Optional[int] = None
    years_experience: Optional[int] = None
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    pan_number: Optional[str] = Field(None, max_length=10)
    gst_number: Optional[str] = Field(None, max_length=15)
    iso_certs: Optional[List[str]] = None
    past_projects: Optional[str] = None
    keywords: Optional[List[str]] = None

class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    sector: Optional[List[str]] = None
    turnover_lakh: Optional[float] = None
    emp_count: Optional[int] = None
    years_experience: Optional[int] = None
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    pan_number: Optional[str] = None
    gst_number: Optional[str] = None
    iso_certs: Optional[List[str]] = None
    past_projects: Optional[str] = None
    keywords: Optional[List[str]] = None

class CompanyResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str]
    sector: Optional[List[str]]
    turnover_lakh: Optional[float]
    emp_count: Optional[int]
    years_experience: Optional[int]
    location_state: Optional[str]
    location_city: Optional[str]
    pan_number: Optional[str]
    gst_number: Optional[str]
    iso_certs: Optional[List[str]]
    past_projects: Optional[str]
    keywords: Optional[List[str]]
    brochure_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    doc_type: str
    file_name: Optional[str]
    file_url: str
    year: Optional[int]
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class BrochureParseResponse(BaseModel):
    """Response from AI brochure parsing — auto-filled company fields."""
    name: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[List[str]] = None
    turnover_lakh: Optional[float] = None
    emp_count: Optional[int] = None
    years_experience: Optional[int] = None
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    iso_certs: Optional[List[str]] = None
    past_projects: Optional[str] = None
    keywords: Optional[List[str]] = None
    confidence: float = Field(ge=0, le=1, description="AI confidence in extraction")
