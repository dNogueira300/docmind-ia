"""Endpoint de auditoría — solo administradores."""
from datetime import datetime
from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.audit_log import AuditLogResponse

router = APIRouter(prefix="/audit-log", tags=["Auditoría"])

AdminOnly = Annotated[User, Depends(require_role("admin"))]


@router.get("/", response_model=list[AuditLogResponse], summary="Ver log de auditoría")
async def list_audit_log(
    current_user: AdminOnly,
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
    Lista el log de auditoría de la organización.
    Filtra por usuario, documento, acción y rango de fechas.
    """
    # Solo ver auditoría de usuarios de la misma organización
    from app.models.user import User as UserModel

    org_user_ids = (
        db.query(UserModel.id)
        .filter(UserModel.organization_id == current_user.organization_id)
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
