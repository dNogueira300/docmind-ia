"""Modelo de alertas de vencimiento detectadas por el pipeline IA."""
import enum
from datetime import date, datetime
from uuid import UUID
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Date, DateTime, ForeignKey, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.organization import Organization


class AlertStatus(str, enum.Enum):
    pending = "pending"
    triggered = "triggered"
    dismissed = "dismissed"


class AlertType(str, enum.Enum):
    expiry = "expiry"
    deadline = "deadline"
    renewal = "renewal"


class DocumentAlert(Base):
    __tablename__ = "document_alerts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    alert_type: Mapped[AlertType] = mapped_column(
        SAEnum(AlertType, name="alert_type", create_type=True),
        nullable=False,
        server_default="expiry",
    )
    detected_date: Mapped[date] = mapped_column(Date, nullable=False)
    alert_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AlertStatus] = mapped_column(
        SAEnum(AlertStatus, name="alert_status", create_type=True),
        nullable=False,
        server_default="pending",
    )
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    document: Mapped["Document"] = relationship(back_populates="alerts")
    organization: Mapped["Organization"] = relationship()
