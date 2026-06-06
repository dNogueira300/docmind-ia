"""Schemas Pydantic para DocumentApproval."""
from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel

from app.models.approval import ApprovalStatus


class ApprovalResponse(BaseModel):
    id: UUID
    document_id: UUID
    organization_id: UUID
    requested_by: UUID
    reviewed_by: Optional[UUID]
    status: ApprovalStatus
    comment: Optional[str]
    requested_at: datetime
    reviewed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ApprovalAction(BaseModel):
    comment: Optional[str] = None
