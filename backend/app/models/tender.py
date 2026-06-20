"""
TenderAI — Tender & TenderMatch Models
Stores scraped government tenders and per-user match scores.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Tender(Base):
    """
    Government tender scraped from eprocure.gov.in, GeM, CPPP, or state portals.
    Contains both raw metadata and processed text for AI analysis.
    """
    __tablename__ = "tenders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    external_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        doc="Portal's own tender reference number",
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Source portal: 'eprocure' | 'gem' | 'cppp' | 'bihar' | 'up' | 'maharashtra'",
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )
    sector: Mapped[list] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="AI-classified sectors: ['solar', 'civil', 'electrical']",
    )
    state: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    department: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Issuing department / ministry",
    )
    organization: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Issuing organization name",
    )
    value_lakh: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        doc="Estimated tender value in Lakhs INR",
    )
    emd_amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        doc="Earnest Money Deposit required",
    )
    tender_fee: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Tender document purchase fee",
    )
    submission_date: Mapped[date] = mapped_column(
        Date,
        nullable=True,
        doc="Last date for bid submission",
    )
    opening_date: Mapped[date] = mapped_column(
        Date,
        nullable=True,
        doc="Bid opening date",
    )
    published_date: Mapped[date] = mapped_column(
        Date,
        nullable=True,
    )
    pdf_url: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Original tender document PDF URL",
    )
    local_pdf_path: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Local storage path of downloaded PDF",
    )
    parsed_text: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Full OCR/extracted text from tender PDF",
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        doc="SHA-256 hash for deduplication",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True,
        doc="Tender lifecycle: 'active' | 'expired' | 'cancelled'",
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────
    matches = relationship(
        "TenderMatch",
        back_populates="tender",
        cascade="all, delete-orphan",
    )
    evaluation_jobs = relationship(
        "EvaluationJob",
        back_populates="tender",
        cascade="all, delete-orphan",
    )
    proposals = relationship(
        "Proposal",
        back_populates="tender",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Tender {self.external_id} [{self.source}] {self.title[:50]}>"

    @property
    def is_expired(self) -> bool:
        if self.submission_date:
            return self.submission_date < date.today()
        return False

    @property
    def days_remaining(self) -> int | None:
        if self.submission_date:
            delta = self.submission_date - date.today()
            return max(0, delta.days)
        return None

class TenderMatch(Base):
    """
    Pre-computed match between a user's company profile and a tender.
    Computed by the matching engine after each scrape run.
    Supports Tinder-style swipe interaction (save / reject).
    """
    __tablename__ = "tender_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "tender_id", name="uq_user_tender_match"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        doc="Match confidence 0.0000 to 1.0000",
    )
    match_reasons: Mapped[list] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Why this matched: ['Sector: Solar', 'State: Bihar', 'Budget: Under 5Cr']",
    )
    is_seen: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    is_saved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="User swiped right / bookmarked",
    )
    is_rejected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="User swiped left",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────
    user = relationship("User", back_populates="tender_matches")
    tender = relationship("Tender", back_populates="matches")

    def __repr__(self) -> str:
        return f"<TenderMatch user={self.user_id} tender={self.tender_id} score={self.match_score}>"
