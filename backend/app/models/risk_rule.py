"""Modelo de reglas de riesgo configurables por organización."""
import enum
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON-stored as array of UUID strings; NULL = aplica a cualquier categoría
    category_ids: Mapped[Optional[list]] = mapped_column(ARRAY(PGUUID(as_uuid=True)), nullable=True)
    keywords: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    min_file_size_kb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, name="risk_level", create_type=True),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("NOW()")
    )

    organization: Mapped["Organization"] = relationship()
