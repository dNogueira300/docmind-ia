"""Solicitudes de demo/acceso desde la landing pública.

Cualquiera puede pedir acceso (nombre + correo + plan de interés). La solicitud
queda pendiente para que el super_admin la revise y "responda" (genera el código
de acceso y un mensaje). El envío de correo NO está implementado todavía: el
mensaje y el código se guardan para entrega manual.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models.base import Base


class DemoRequest(Base):
    __tablename__ = "demo_requests"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Plan de interés (free/pro/enterprise).
    plan: Mapped[str] = mapped_column(String(20), nullable=False, server_default="'free'")
    # Nota opcional del solicitante.
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # pending | responded
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="'pending'")
    # Respuesta del super_admin (simula el cuerpo del correo).
    response_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Código de activación generado al responder (si aplica).
    activation_code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    responded_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
