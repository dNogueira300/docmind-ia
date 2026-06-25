"""Código de activación que un admin canjea para activar un plan de pago.

Lo genera el super_admin (venta manual: transferencia, Yape, etc.) y el admin de
la organización lo canjea para "voltear" el plan de su empresa. La fuente de verdad
sigue siendo `organizations.plan`; el código es solo el mecanismo de entrega.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models.base import Base


class ActivationCode(Base):
    __tablename__ = "activation_codes"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    # Plan que activa el código (free/pro/enterprise).
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    # Días de vigencia del plan una vez canjeado.
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="365")
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    used_by_org: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Vigencia del propio código (hasta cuándo se puede canjear). NULL = sin límite.
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
