"""Modelo de la tabla audit_log — INMUTABLE, solo INSERT."""
import enum
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, DateTime, ForeignKey, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.user import User


class AuditAction(str, enum.Enum):
    upload = "upload"
    view = "view"
    download = "download"
    reclassify = "reclassify"
    delete = "delete"
    login = "login"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, name="audit_action", create_type=False),
        nullable=False,
    )
    detail_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    # Relaciones
    document: Mapped[Optional["Document"]] = relationship(back_populates="audit_entries")
    user: Mapped["User"] = relationship(back_populates="audit_entries")
