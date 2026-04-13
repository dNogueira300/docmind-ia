"""Schemas Pydantic para Organization."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
