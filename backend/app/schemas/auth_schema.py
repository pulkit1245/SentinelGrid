from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    pass  # refresh token comes from HttpOnly cookie


class UserInToken(BaseModel):
    user_id: str
    email: str
    role: str
    plant_id: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    full_name: str | None = None
    is_active: bool
