"""
Foedus — Auth Router
Register, login, token refresh, and current-user endpoints.
JWT-based auth (access + refresh tokens).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.utils.logger import logger
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _issue_tokens(user: User) -> TokenResponse:
    """Create an access + refresh token pair for a user."""
    payload = {"sub": str(user.id), "email": user.email, "plan": user.plan}
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new user account and return tokens (auto-login).
    """
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=body.email.lower(),
        password=hash_password(body.password),
        full_name=body.full_name,
        plan="free",
        # MVP: skip email verification flow; mark verified on signup.
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"🆕 New user registered: {user.email}")
    return _issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate with email + password. Returns access + refresh tokens.
    """
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    # Same error for wrong email or wrong password (no user enumeration)
    if user is None or not verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended. Contact support.",
        )

    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(body: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    """
    payload = decode_refresh_token(body.refresh_token)
    if payload is None or payload.get("sub") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Malformed token subject.")

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    return _issue_tokens(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Return the authenticated user's profile.
    """
    return current_user
