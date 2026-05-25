"""Schemas Pydantic para Organization (tenant)."""
import re
from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole


_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_slug(v: str) -> str:
    v = (v or "").strip().lower()
    if not v:
        raise ValueError("El slug no puede estar vacío")
    if len(v) < 2 or len(v) > 50:
        raise ValueError("El slug debe tener entre 2 y 50 caracteres")
    if not _SLUG_RE.match(v):
        raise ValueError(
            "El slug solo puede contener minúsculas, números y guiones "
            "(ej. 'maynas', 'staff-abogados')"
        )
    if v in {"admin", "api", "login", "logout", "system", "public", "static"}:
        raise ValueError(f"El slug '{v}' está reservado por el sistema")
    return v


class OrganizationPublic(BaseModel):
    """Datos públicos de una organización (para mostrar en la página de login)."""
    id: UUID
    name: str
    slug: str
    active: bool

    model_config = {"from_attributes": True}


class OrganizationResponse(OrganizationPublic):
    """Vista completa — solo expuesta a super_admin."""
    created_at: datetime
    updated_at: datetime


class OrganizationCreate(BaseModel):
    name: str
    slug: str
    # Opcional: crear también el admin inicial de la empresa en un solo paso.
    admin_name: Optional[str] = None
    admin_email: Optional[EmailStr] = None
    admin_password: Optional[str] = None

    @field_validator("slug")
    @classmethod
    def _slug_ok(cls, v: str) -> str:
        return _validate_slug(v)

    @field_validator("admin_password")
    @classmethod
    def _password_ok(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("La contraseña del admin debe tener al menos 8 caracteres")
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    active: Optional[bool] = None

    @field_validator("slug")
    @classmethod
    def _slug_ok(cls, v: Optional[str]) -> Optional[str]:
        return _validate_slug(v) if v is not None else None


class OrganizationStats(BaseModel):
    """Métricas resumidas por organización (para el panel super admin)."""
    id: UUID
    name: str
    slug: str
    active: bool
    users_count: int
    categories_count: int
    documents_count: int
    storage_kb: int


class CreateAdminInOrg(BaseModel):
    """Crear o reemplazar el administrador principal de una organización."""
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def _password_ok(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v
