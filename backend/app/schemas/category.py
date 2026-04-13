"""Schemas Pydantic para Category."""
from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, field_validator
import re


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#2563D4"

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("El color debe ser un hex válido, por ejemplo #2563D4")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre de la categoría no puede estar vacío")
        return v.strip()


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("El color debe ser un hex válido, por ejemplo #2563D4")
        return v


class CategoryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str]
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}
