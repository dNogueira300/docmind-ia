"""Schemas Pydantic para User. Nunca exponer password_hash."""
from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.consultor

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    active: Optional[bool] = None


class UserResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    email: str
    role: UserRole
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
