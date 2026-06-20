"""
Foedus — Company & Document Vault Models
Stores SME company profiles and their uploaded certificates/documents.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Company(Base):
    """
    Company profile for an SME.
    One user has one company (MVP constraint).
    Contains all context the AI agents need for tender matching & evaluation.
    """
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Company overview / elevator pitch",
    )
    sector: Mapped[list] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Industry sectors: ['solar', 'civil', 'it', 'pharma']",
    )
    turnover_lakh: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Annual turnover in Lakhs INR",
    )
    emp_count: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        doc="Total employee count",
    )
    years_experience: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        doc="Years in business",
    )
    location_state: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )
    location_city: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )
    pan_number: Mapped[str] = mapped_column(
        String(10),
        nullable=True,
    )
    gst_number: Mapped[str] = mapped_column(
        String(15),
        nullable=True,
    )
    iso_certs: Mapped[list] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="ISO certifications: ['ISO 9001', 'ISO 14001']",
    )
    past_projects: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Summary of past projects for proposal generation",
    )
    keywords: Mapped[list] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Auto-extracted keywords from brochure for matching",
    )
    brochure_url: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="URL of uploaded company brochure PDF",
    )
    # Note: pgvector embedding stored separately or via pgvector column
    # For MVP, we use Qdrant for vector operations instead
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────
    user = relationship("User", back_populates="company")
    documents = relationship(
        "CompanyDocument",
        back_populates="company",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Company {self.name} [{', '.join(self.sector or [])}]>"

class CompanyDocument(Base):
    """
    Document vault: uploaded certificates, audit reports, balance sheets, etc.
    The AI auditor agent uses these to cross-check tender eligibility criteria.
    """
    __tablename__ = "company_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    doc_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Document type: 'audit_report' | 'gst_cert' | 'pan' | 'iso_cert' | 'portfolio' | 'balance_sheet' | 'experience_cert'",
    )
    file_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Storage URL (Supabase / local path)",
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
    )
    year: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        doc="Relevant year (e.g., FY2023 for balance sheets)",
    )
    parsed_text: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="OCR/extracted text content — agent context",
    )
    is_verified: Mapped[bool] = mapped_column(
        default=False,
        doc="Admin verified document",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────
    company = relationship("Company", back_populates="documents")

    def __repr__(self) -> str:
        return f"<CompanyDocument {self.doc_type} [{self.file_name}]>"
