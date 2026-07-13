"""
Foedus — Proposal Schemas
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

class ProposalCreate(BaseModel):
    tender_id: uuid.UUID
    evaluation_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    content_md: Optional[str] = None

class ProposalUpdate(BaseModel):
    title: Optional[str] = None
    content_md: Optional[str] = None
    status: Optional[str] = None

class ProposalResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    tender_id: uuid.UUID
    evaluation_id: Optional[uuid.UUID]
    title: Optional[str]
    content_md: Optional[str]
    version: int
    status: str
    pdf_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
