import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.user import UserRole


class UserBase(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=32)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Invalid email format")
        return clean


class UserCreate(UserBase):
    password: str = Field(min_length=8)
    role: UserRole = UserRole.CITIZEN
    organization_id: Optional[uuid.UUID] = None
    jurisdiction_id: Optional[uuid.UUID] = None


class UserRegister(UserBase):
    password: str = Field(min_length=8)


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: UserRole
    organization_id: Optional[uuid.UUID] = None
    jurisdiction_id: Optional[uuid.UUID] = None
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
