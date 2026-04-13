"""Modelo de la tabla documents con ciclo de vida de estados."""
import enum
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.category import Category
    from app.models.user import User
    from app.models.audit_log import AuditLog


class DocStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    classified = "classified"
    review = "review"
    error = "error"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_kb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, name="doc_status", create_type=False),
        nullable=False,
        server_default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()"),
        onupdate=datetime.utcnow,
    )

    # Relaciones
    organization: Mapped["Organization"] = relationship(back_populates="documents")
    category: Mapped[Optional["Category"]] = relationship(back_populates="documents")
    uploader: Mapped["User"] = relationship(
        back_populates="documents", foreign_keys=[uploaded_by]
    )
    audit_entries: Mapped[list["AuditLog"]] = relationship(back_populates="document")
