"""
Foedus — Payments Router (Razorpay)
One-time ₹999 order → 30 days of Pro. No SDK: orders via httpx REST,
signature verification via stdlib HMAC (as per Razorpay docs).

Flow:
1. POST /payments/create-order  → Razorpay order_id (frontend opens Checkout)
2. Checkout success             → POST /payments/verify with signature
3. Signature valid              → Subscription active, user.plan = 'pro'
4. POST /payments/webhook       → server-side safety net (payment.captured)
"""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import Subscription
from app.models.user import User
from app.utils.billing import (
    PLANS,
    PRO_PERIOD_DAYS,
    PRO_PRICE_PAISE,
    ensure_plan_current,
    get_active_subscription,
)
from app.utils.logger import logger

router = APIRouter(prefix="/payments", tags=["Payments"])

RAZORPAY_API = "https://api.razorpay.com/v1"


class VerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def _verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """HMAC-SHA256 of 'order_id|payment_id' with the key secret."""
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _activate_pro(user: User, sub: Subscription, db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    sub.status = "active"
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=PRO_PERIOD_DAYS)
    user.plan = "pro"
    user.evals_used = 0  # fresh month
    await db.commit()
    logger.info(f"💳 Pro activated: {user.email} until {sub.current_period_end:%Y-%m-%d}")


@router.get("/plans")
async def list_plans():
    """Public plan catalogue for the pricing UI."""
    return PLANS


@router.get("/subscription")
async def my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current billing state for the billing page."""
    user = await ensure_plan_current(current_user, db)
    sub = await get_active_subscription(user, db)
    return {
        "plan": user.plan,
        "evals_used": user.evals_used,
        "eval_limit": None if user.plan == "pro" else user.eval_limit,
        "period_end": sub.current_period_end if sub else None,
    }


@router.post("/create-order", status_code=status.HTTP_201_CREATED)
async def create_order(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Razorpay order for the Pro plan.
    Returns everything the frontend Checkout needs.
    """
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payments not configured on this server")

    user = await ensure_plan_current(current_user, db)
    if user.plan == "pro":
        raise HTTPException(status_code=409, detail="You are already on Pro 🎉")

    async with httpx.AsyncClient(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        timeout=20,
    ) as client:
        resp = await client.post(
            f"{RAZORPAY_API}/orders",
            json={
                "amount": PRO_PRICE_PAISE,
                "currency": "INR",
                "receipt": f"foedus_{str(user.id)[:16]}",
                "notes": {"user_id": str(user.id), "plan": "pro"},
            },
        )
    if resp.status_code != 200:
        logger.error(f"Razorpay order failed: {resp.status_code} {resp.text[:200]}")
        raise HTTPException(status_code=502, detail="Payment gateway error. Try again.")

    order = resp.json()

    sub = Subscription(
        user_id=user.id,
        razorpay_order_id=order["id"],
        plan="pro",
        amount_paise=PRO_PRICE_PAISE,
        status="pending",
    )
    db.add(sub)
    await db.commit()

    return {
        "order_id": order["id"],
        "amount": PRO_PRICE_PAISE,
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID,
        "name": "Foedus Pro",
        "description": f"Unlimited AI evaluations · {PRO_PERIOD_DAYS} days",
        "prefill_email": user.email,
    }


@router.post("/verify")
async def verify_payment(
    body: VerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by the frontend after Checkout success.
    Verifies the signature and activates Pro.
    """
    if not _verify_signature(
        body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature
    ):
        logger.warning(f"💳 BAD payment signature from {current_user.email}")
        raise HTTPException(status_code=400, detail="Payment signature verification failed")

    sub = (
        await db.execute(
            select(Subscription).where(
                Subscription.razorpay_order_id == body.razorpay_order_id,
                Subscription.user_id == current_user.id,
            )
        )
    ).scalars().first()
    if sub is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if sub.status != "active":
        sub.razorpay_sub_id = body.razorpay_payment_id
        await _activate_pro(current_user, sub, db)

    return {"status": "active", "plan": "pro", "period_end": sub.current_period_end}


@router.post("/webhook", include_in_schema=False)
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Server-side safety net: activates Pro even if the user closed the tab
    before /verify fired. Configure in Razorpay dashboard →
    event `payment.captured`, secret = RAZORPAY_WEBHOOK_SECRET.
    """
    raw = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(), raw, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = await request.json()
    if payload.get("event") != "payment.captured":
        return {"status": "ignored"}

    entity = payload["payload"]["payment"]["entity"]
    order_id = entity.get("order_id")

    sub = (
        await db.execute(
            select(Subscription).where(Subscription.razorpay_order_id == order_id)
        )
    ).scalars().first()
    if sub is None:
        logger.warning(f"💳 Webhook for unknown order {order_id}")
        return {"status": "unknown_order"}

    if sub.status != "active":
        user = await db.get(User, sub.user_id)
        if user:
            sub.razorpay_sub_id = entity.get("id")
            await _activate_pro(user, sub, db)

    return {"status": "ok"}
