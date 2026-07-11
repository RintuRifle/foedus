"""
Foedus — Tenders Router
Personalized tender feed, search, detail, and Tinder-style swipe actions.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.tender import Tender, TenderMatch
from app.models.user import User
from app.schemas.tender import (
    TenderFeedItem,
    TenderListResponse,
    TenderResponse,
)
from app.utils.logger import logger

router = APIRouter(prefix="/tenders", tags=["Tenders"])


def _to_feed_item(tender: Tender, match: Optional[TenderMatch]) -> TenderFeedItem:
    resp = TenderResponse.model_validate(tender)
    resp.days_remaining = tender.days_remaining
    return TenderFeedItem(
        tender=resp,
        match_score=float(match.match_score) if match else 0.0,
        match_reasons=match.match_reasons if match else None,
        is_saved=match.is_saved if match else False,
        is_seen=match.is_seen if match else False,
    )


@router.get("/feed", response_model=TenderListResponse)
async def get_personalized_feed(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    min_score: float = Query(default=0.5, ge=0, le=1),
    include_seen: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Personalized "Daily Matches" feed.
    Returns active tenders pre-matched to the user's company profile,
    sorted by match score (best first). Rejected tenders are excluded.
    """
    filters = [
        TenderMatch.user_id == current_user.id,
        TenderMatch.match_score >= min_score,
        TenderMatch.is_rejected.is_(False),
        Tender.status == "active",
    ]
    if not include_seen:
        filters.append(TenderMatch.is_seen.is_(False))

    base = (
        select(TenderMatch, Tender)
        .join(Tender, TenderMatch.tender_id == Tender.id)
        .where(and_(*filters))
    )

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(desc(TenderMatch.match_score))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()

    items = [_to_feed_item(tender, match) for match, tender in rows]
    return TenderListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        has_next=page * per_page < total,
    )


@router.get("/saved", response_model=TenderListResponse)
async def get_saved_tenders(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tenders the user swiped right on (bookmarked)."""
    base = (
        select(TenderMatch, Tender)
        .join(Tender, TenderMatch.tender_id == Tender.id)
        .where(
            TenderMatch.user_id == current_user.id,
            TenderMatch.is_saved.is_(True),
        )
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            base.order_by(desc(TenderMatch.created_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()

    items = [_to_feed_item(tender, match) for match, tender in rows]
    return TenderListResponse(
        items=items, total=total, page=page, per_page=per_page,
        has_next=page * per_page < total,
    )


@router.get("/search", response_model=TenderListResponse)
async def search_tenders(
    q: Optional[str] = Query(default=None, description="Keyword search in title/description"),
    state: Optional[str] = None,
    sector: Optional[str] = None,
    source: Optional[str] = None,
    min_value: Optional[float] = Query(default=None, description="Min tender value (Lakh)"),
    max_value: Optional[float] = Query(default=None, description="Max tender value (Lakh)"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manual keyword/filter search across all active tenders
    (independent of the AI match feed).
    """
    filters = [Tender.status == "active"]
    if q:
        pattern = f"%{q}%"
        filters.append(or_(Tender.title.ilike(pattern), Tender.description.ilike(pattern)))
    if state:
        filters.append(Tender.state.ilike(state))
    if source:
        filters.append(Tender.source == source)
    if sector:
        filters.append(Tender.sector.any(sector.lower()))
    if min_value is not None:
        filters.append(Tender.value_lakh >= min_value)
    if max_value is not None:
        filters.append(Tender.value_lakh <= max_value)

    base = select(Tender).where(and_(*filters))
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    tenders = (
        await db.execute(
            base.order_by(desc(Tender.published_date).nulls_last())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    # Attach the user's match rows where they exist
    tender_ids = [t.id for t in tenders]
    matches = {}
    if tender_ids:
        match_rows = (
            await db.execute(
                select(TenderMatch).where(
                    TenderMatch.user_id == current_user.id,
                    TenderMatch.tender_id.in_(tender_ids),
                )
            )
        ).scalars().all()
        matches = {m.tender_id: m for m in match_rows}

    items = [_to_feed_item(t, matches.get(t.id)) for t in tenders]
    return TenderListResponse(
        items=items, total=total, page=page, per_page=per_page,
        has_next=page * per_page < total,
    )


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender(
    tender_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full tender detail. Marks the user's match as 'seen'."""
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Mark seen (fire-and-forget semantics)
    match = (
        await db.execute(
            select(TenderMatch).where(
                TenderMatch.user_id == current_user.id,
                TenderMatch.tender_id == tender_id,
            )
        )
    ).scalar_one_or_none()
    if match and not match.is_seen:
        match.is_seen = True
        await db.commit()

    resp = TenderResponse.model_validate(tender)
    resp.days_remaining = tender.days_remaining
    return resp


async def _get_or_create_match(
    db: AsyncSession, user_id: uuid.UUID, tender_id: uuid.UUID
) -> TenderMatch:
    match = (
        await db.execute(
            select(TenderMatch).where(
                TenderMatch.user_id == user_id,
                TenderMatch.tender_id == tender_id,
            )
        )
    ).scalar_one_or_none()
    if match is None:
        # User acted on a tender outside their feed (e.g. via search)
        match = TenderMatch(
            user_id=user_id, tender_id=tender_id,
            match_score=0.0, is_seen=True,
        )
        db.add(match)
    return match


@router.post("/{tender_id}/save", status_code=status.HTTP_200_OK)
async def save_tender(
    tender_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Swipe right — bookmark this tender."""
    if not await db.get(Tender, tender_id):
        raise HTTPException(status_code=404, detail="Tender not found")
    match = await _get_or_create_match(db, current_user.id, tender_id)
    match.is_saved = True
    match.is_rejected = False
    match.is_seen = True
    await db.commit()
    return {"tender_id": str(tender_id), "is_saved": True}


@router.post("/{tender_id}/reject", status_code=status.HTTP_200_OK)
async def reject_tender(
    tender_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Swipe left — hide this tender from the feed."""
    if not await db.get(Tender, tender_id):
        raise HTTPException(status_code=404, detail="Tender not found")
    match = await _get_or_create_match(db, current_user.id, tender_id)
    match.is_rejected = True
    match.is_saved = False
    match.is_seen = True
    await db.commit()
    return {"tender_id": str(tender_id), "is_rejected": True}
