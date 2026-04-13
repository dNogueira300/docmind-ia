"""Schemas Pydantic para AuditLog."""
from datetime import datetime
from uuid import UUID
from typing import Optional, Any

from pydantic import BaseModel

from app.models.audit_log import AuditAction


class AuditLogResponse(BaseModel):
    id: UUID
    document_id: Optional[UUID]
    user_id: UUID
    action: AuditAction
    detail_json: Optional[Any]
    ip_address: Optional[str]
    timestamp: datetime

    model_config = {"from_attributes": True}
