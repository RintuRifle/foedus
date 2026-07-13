"""
Foedus — Billing Helpers
Plan definitions and expiry enforcement.
No Razorpay SDK — orders via httpx, signatures via stdlib hmac.
"""

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Subscription
from app.models.user import User
from app.utils.logger import logger

# ── Plans (single source of truth) ───────────────────────────
PLANS = {
    "free": {
        "name": "Free",
        "price_inr": 0,
        "evals_per_month": 3,
        "features": ["3 AI evaluations / month", "Daily tender matches", "Compliance reports"],
    },
    "pro": {
        "name": "Pro",
        "price_inr": 999,
        "evals_per_month": None,  # unlimited
        "features": [
            "Unlimited AI evaluations",
            "Auto proposal drafting + PDF export",
            "Priority evaluation queue",
            "Deadline alerts",
        ],
    },
}

PRO_PRICE_PAISE = PLANS["pro"]["price_inr"] * 100
PRO_PERIOD_DAYS = 30


async def get_active_subscription(
    user: User, db: AsyncSession
) -> Subscription | None:
    """Latest active subscription, if any."""
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(desc(Subscription.current_period_end))
        .limit(1)
    )
    return result.scalars().first()


async def ensure_plan_current(user: User, db: AsyncSession) -> User:
    """
    Enforce plan expiry: a 'pro' user whose subscription period has ended
    is downgraded to 'free' (and the subscription marked expired).
    Call this before any quota-gated action.
    """
    if user.plan not in ("pro", "starter", "enterprise"):
        return user

    sub = await get_active_subscription(user, db)
    now = datetime.now(timezone.utc)

    if sub is None or (sub.current_period_end and sub.current_period_end < now):
        if sub is not None:
            sub.status = "expired"
        user.plan = "free"
        await db.commit()
        logger.info(f"💳 Plan expired → downgraded {user.email} to free")
    return user
