"""
Foedus — User Model
Handles authentication, plan management, and usage tracking.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="bcrypt hashed password",
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )
    plan: Mapped[str] = mapped_column(
        String(20),
        default="free",
        nullable=False,
        doc="free | starter | pro | enterprise | admin",
    )
    evals_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Monthly evaluation counter — reset on billing cycle",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="Email verified flag",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        doc="Soft delete / account suspension flag",
    )
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
    company = relationship(
        "Company",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    evaluation_jobs = relationship(
        "EvaluationJob",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    proposals = relationship(
        "Proposal",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    tender_matches = relationship(
        "TenderMatch",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.plan}]>"

    @property
    def eval_limit(self) -> int:
        """Monthly evaluation limit based on plan."""
        limits = {
            "free": 3,
            "starter": 15,
            "pro": 999999,       # Effectively unlimited
            "enterprise": 999999,
            "admin": 999999,
        }
        return limits.get(self.plan, 3)

    @property
    def can_evaluate(self) -> bool:
        """Check if user has remaining evaluations this month."""
        return self.evals_used < self.eval_limit
