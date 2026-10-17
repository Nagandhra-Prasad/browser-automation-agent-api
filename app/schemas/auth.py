from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["user", "admin"] = "user"
    admin_code: str | None = Field(
        default=None,
        description="Required when role is admin",
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Literal["user", "admin"]
    onboarding_completed: bool = False
    is_active: bool = True
    created_at: datetime


class UserActiveUpdate(BaseModel):
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
