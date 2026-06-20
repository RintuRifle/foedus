"""
Foedus — Notification & Subscription Models
In-app alerts, email/WhatsApp notifications, and Razorpay subscription tracking.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, doc="new_match | eval_complete | deadline_alert | payment_success | system")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[dict] = mapped_column(JSONB, nullable=True, doc="Extra data: {tender_id, job_id, etc.}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification [{self.type}] {self.title[:30]}>"

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    razorpay_sub_id: Mapped[str] = mapped_column(String(255), nullable=True, unique=True)
    razorpay_order_id: Mapped[str] = mapped_column(String(255), nullable=True)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, doc="starter | pro | enterprise")
    amount_paise: Mapped[int] = mapped_column(nullable=True, doc="Amount in paise (999*100 = 99900)")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", doc="pending | active | cancelled | expired")
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription [{self.plan}] {self.status}>"
