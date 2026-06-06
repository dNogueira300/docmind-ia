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
    organization_id: Optional[UUID] = None  # None solo para super_admin
    name: str
    email: str
    role: UserRole
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class GlobalAdminCreate(BaseModel):
    """Crea un admin en cualquier organización (solo super_admin)."""
    organization_id: UUID
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class GlobalAdminUpdate(BaseModel):
    """Edita nombre y/o email de un admin (solo super_admin)."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class GlobalAdminPasswordUpdate(BaseModel):
    """Cambia la contraseña de un admin (solo super_admin)."""
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class GlobalAdminResponse(BaseModel):
    """Respuesta enriquecida con nombre de empresa para el panel super_admin."""
    id: UUID
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None
    name: str
    email: str
    role: UserRole
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
