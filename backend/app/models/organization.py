"""Modelo de la tabla organizations (raíz de multitenancy)."""
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category
    from app.models.document import Document


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    # Relaciones
    users: Mapped[list["User"]] = relationship(back_populates="organization")
    categories: Mapped[list["Category"]] = relationship(back_populates="organization")
    documents: Mapped[list["Document"]] = relationship(back_populates="organization")
