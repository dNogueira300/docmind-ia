"""Schemas Pydantic para RiskRule."""
from datetime import datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel

from app.models.risk_rule import RiskLevel


class RiskRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_ids: Optional[List[UUID]] = None
    keywords: Optional[List[str]] = None
    min_file_size_kb: Optional[int] = None
    risk_level: RiskLevel
    active: bool = True


class RiskRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_ids: Optional[List[UUID]] = None
    keywords: Optional[List[str]] = None
    min_file_size_kb: Optional[int] = None
    risk_level: Optional[RiskLevel] = None
    active: Optional[bool] = None


class RiskRuleResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str]
    category_ids: Optional[List[UUID]]
    keywords: Optional[List[str]]
    min_file_size_kb: Optional[int]
    risk_level: RiskLevel
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
