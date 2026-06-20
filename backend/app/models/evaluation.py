"""
Foedus — Evaluation Job & Compliance Item Models
Tracks the AI agent pipeline execution and stores structured results.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class EvaluationJob(Base):
    __tablename__ = "evaluation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False, index=True)
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    current_agent: Mapped[str] = mapped_column(String(50), nullable=True)
    current_message: Mapped[str] = mapped_column(Text, nullable=True)
    match_result: Mapped[dict] = mapped_column(JSONB, nullable=True)
    audit_result: Mapped[dict] = mapped_column(JSONB, nullable=True)
    risk_result: Mapped[dict] = mapped_column(JSONB, nullable=True)
    final_result: Mapped[dict] = mapped_column(JSONB, nullable=True)
    error_log: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="evaluation_jobs")
    tender = relationship("Tender", back_populates="evaluation_jobs")
    compliance_items = relationship("ComplianceItem", back_populates="evaluation_job", cascade="all, delete-orphan")
    proposal = relationship("Proposal", back_populates="evaluation_job", uselist=False)

    def __repr__(self) -> str:
        return f"<EvaluationJob {self.id} [{self.status}]>"

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

class ComplianceItem(Base):
    __tablename__ = "compliance_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=True)
    required_value: Mapped[str] = mapped_column(Text, nullable=True)
    user_value: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    source_quote: Mapped[str] = mapped_column(Text, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    evaluation_job = relationship("EvaluationJob", back_populates="compliance_items")

    def __repr__(self) -> str:
        return f"<ComplianceItem [{self.status}] {self.criterion[:40]}>"
