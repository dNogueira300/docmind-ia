"""Schemas Pydantic para DocumentAlert."""
from datetime import date, datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel

from app.models.alert import AlertType, AlertStatus


class AlertResponse(BaseModel):
    id: UUID
    document_id: UUID
    document_name: Optional[str] = None   # nombre del archivo para mostrar en UI
    organization_id: UUID
    alert_type: AlertType
    detected_date: date
    alert_date: date
    status: AlertStatus
    detail: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
