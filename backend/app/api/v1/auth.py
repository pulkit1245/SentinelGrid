from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, verify_password, decode_token
from app.middlewares.rate_limiter import rate_limit
from app.models.base import get_db
from app.models.user import User
from app.schemas.auth_schema import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit(5, 60))])
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Authenticate user and issue JWT access token + HttpOnly refresh cookie."""
    user = None
    try:
        result = await db.execute(select(User).where(User.email == body.email, User.is_active == True))
        user = result.scalar_one_or_none()
    except Exception:
        pass  # DB connection optional for demo login fallback

    token_data = None
    if user and verify_password(body.password, user.password_hash):
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "plant_id": str(user.plant_id) if user.plant_id else None,
        }
    elif body.email in ("admin@sentinelgrid.demo", "officer@sentinelgrid.demo") and body.password == "Demo@1234":
        is_admin = body.email.startswith("admin")
        token_data = {
            "sub": "00000000-0000-0000-0000-000000000001" if is_admin else "00000000-0000-0000-0000-000000000002",
            "email": body.email,
            "role": "plant_admin" if is_admin else "safety_officer",
            "plant_id": "00000000-0000-0000-0000-000000000001",
        }

    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Refresh token goes in HttpOnly cookie — never accessible to JS
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",  # False on localhost http
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/api/v1/auth/refresh",
    )

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
):
    """Silently issue a new access token using the HttpOnly refresh cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
    )

    if not refresh_token:
        raise credentials_exception

    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception
    except Exception:
        raise credentials_exception

    # Re-issue access token with same claims
    token_data = {
        "sub": payload["sub"],
        "email": payload.get("email", ""),
        "role": payload.get("role", ""),
        "plant_id": payload.get("plant_id"),
    }
    return TokenResponse(access_token=create_access_token(token_data))


@router.post("/logout")
async def logout(response: Response):
    """Clear refresh token cookie."""
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
    return {"message": "Logged out successfully"}
