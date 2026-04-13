"""Modelo de la tabla categories (personalizable por organización)."""
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.document import Document


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, server_default="'#2563D4'")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    # Relaciones
    organization: Mapped["Organization"] = relationship(back_populates="categories")
    documents: Mapped[list["Document"]] = relationship(back_populates="category")
