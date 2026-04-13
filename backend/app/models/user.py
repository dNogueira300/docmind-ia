"""Modelo de la tabla users con enum user_role."""
import enum
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.document import Document
    from app.models.audit_log import AuditLog


class UserRole(str, enum.Enum):
    admin = "admin"
    editor = "editor"
    consultor = "consultor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_type=False),
        nullable=False,
        server_default="consultor",
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    # Relaciones
    organization: Mapped["Organization"] = relationship(back_populates="users")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="uploader", foreign_keys="Document.uploaded_by"
    )
    audit_entries: Mapped[list["AuditLog"]] = relationship(back_populates="user")
