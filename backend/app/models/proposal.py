"""
Foedus — Proposal Model
Stores AI-generated proposals that users can edit and export as PDF.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_jobs.id"), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=True)
    content_md: Mapped[str] = mapped_column(Text, nullable=True, doc="Full proposal in Markdown format")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="draft", doc="draft | reviewed | submitted | archived")
    pdf_url: Mapped[str] = mapped_column(Text, nullable=True, doc="Generated PDF storage URL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="proposals")
    tender = relationship("Tender", back_populates="proposals")
    evaluation_job = relationship("EvaluationJob", back_populates="proposal")

    def __repr__(self) -> str:
        return f"<Proposal {self.id} v{self.version} [{self.status}]>"
