"""Schemas para las solicitudes de demo/acceso."""
from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class DemoRequestCreate(BaseModel):
    """Lo que envía el formulario público de la landing."""
    name: str
    email: EmailStr
    organization_name: Optional[str] = None
    plan: str = "free"
    message: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_ok(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El nombre es obligatorio")
        return v.strip()


class DemoRequestResponse(BaseModel):
    id: UUID
    name: str
    email: str
    organization_name: Optional[str] = None
    plan: str
    message: Optional[str] = None
    status: str
    response_message: Optional[str] = None
    activation_code: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DemoRequestRespond(BaseModel):
    """Acción del super_admin: responder (simula el correo) y opcionalmente crear acceso."""
    message: str
    generate_code: bool = True
    plan: Optional[str] = None        # si None, usa el plan de la solicitud
    duration_days: int = 30

    @field_validator("message")
    @classmethod
    def _msg_ok(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El mensaje de respuesta no puede estar vacío")
        return v.strip()
