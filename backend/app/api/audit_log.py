"""Endpoint de auditoría — aislado por tenant."""
from datetime import datetime
from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_company_admin, get_active_organization_id
from app.models.user import User as UserModel
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.audit_log import AuditLogResponse

router = APIRouter(prefix="/audit-log", tags=["Auditoría"])

CompanyAdmin = Annotated[UserModel, Depends(require_company_admin)]


@router.get("/", response_model=list[AuditLogResponse], summary="Ver log de auditoría")
async def list_audit_log(
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[UUID] = Query(None),
    document_id: Optional[UUID] = Query(None),
    action: Optional[AuditAction] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
) -> list[AuditLog]:
    """
    Lista el log de auditoría de la empresa activa.
    Solo incluye entradas de usuarios que pertenecen a esa empresa.
    """
    org_user_ids = (
        db.query(UserModel.id)
        .filter(UserModel.organization_id == organization_id)
        .subquery()
    )

    q = db.query(AuditLog).filter(AuditLog.user_id.in_(org_user_ids))

    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if document_id:
        q = q.filter(AuditLog.document_id == document_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if from_date:
        q = q.filter(AuditLog.timestamp >= from_date)
    if to_date:
        q = q.filter(AuditLog.timestamp <= to_date)

    return q.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
