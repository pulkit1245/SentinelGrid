from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.models.base import get_db
from app.models.user import User
from app.schemas.auth_schema import UserInToken

logger = logging.getLogger(__name__)


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> UserInToken:
    """FastAPI dependency: validates Bearer JWT and returns parsed user info."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub", "")
        email: str = payload.get("email", "")
        role: str = payload.get("role", "")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return UserInToken(
        user_id=user_id,
        email=email,
        role=role,
        plant_id=payload.get("plant_id"),
    )


def require_role(*allowed_roles: str):
    """Dependency factory: restricts an endpoint to specific roles."""

    async def _check(current_user: UserInToken = Depends(get_current_user)) -> UserInToken:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorised for this action",
            )
        return current_user

    return _check


async def verify_service_token(
    x_service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None,
) -> None:
    """Dependency: validates the internal service token used by the simulator/workers."""
    if x_service_token != settings.SERVICE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
        )


async def get_ws_user_from_token(token: str) -> UserInToken:
    """Parse JWT from WebSocket query param (token=...) for handshake auth."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Not an access token")
        return UserInToken(
            user_id=payload["sub"],
            email=payload.get("email", ""),
            role=payload.get("role", ""),
            plant_id=payload.get("plant_id"),
        )
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
