from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., description="Email or username credential")
    password: str = Field(..., description="Plain password")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Cryptographically signed or opaque refresh token")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenPayload(BaseModel):
    sub: str
    email: str
    role: str
    exp: int
    type: str = "access"
