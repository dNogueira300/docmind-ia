"""Precios editables que se muestran en la página pública de precios.

Una fila por plan (free/pro/enterprise). El super_admin los ajusta desde su panel;
la landing pública los lee sin autenticación. Los LÍMITES y FEATURES siguen viniendo
de app/core/plans.py (código); aquí solo vive lo comercial (precio, moneda, etc.).
"""
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional

from sqlalchemy import String, Boolean, Numeric, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models.base import Base


class PlanPricing(Base):
    __tablename__ = "plan_pricing"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    plan: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default="0")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, server_default="'S/'")
    period: Mapped[str] = mapped_column(String(20), nullable=False, server_default="'/mes'")
    tagline: Mapped[Optional[str]] = mapped_column(String(140), nullable=True)
    # Marca visual de "recomendado" en la landing.
    highlight: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Si es True, en vez del precio se muestra "Cotización" (ej. enterprise).
    custom_quote: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()"),
        onupdate=datetime.utcnow,
    )
