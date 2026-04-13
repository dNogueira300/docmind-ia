"""Schemas Pydantic para Document."""
from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel

from app.models.document import DocStatus


class DocumentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    category_id: Optional[UUID]
    uploaded_by: UUID
    original_filename: str
    stored_path: str
    file_type: str
    file_size_kb: Optional[int]
    ocr_text: Optional[str]
    ai_confidence_score: Optional[float]
    status: DocStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentReclassify(BaseModel):
    category_id: UUID


class DocumentListResponse(BaseModel):
    """Respuesta de listado sin exponer ocr_text completo."""
    id: UUID
    organization_id: UUID
    category_id: Optional[UUID]
    uploaded_by: UUID
    original_filename: str
    file_type: str
    file_size_kb: Optional[int]
    ai_confidence_score: Optional[float]
    status: DocStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
