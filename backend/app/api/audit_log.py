"""Endpoint de auditoría — aislado por tenant; global para super_admin sin tenant."""
from datetime import datetime
from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import require_company_admin
from app.models.user import User as UserModel
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.audit_log import AuditLogResponse

router = APIRouter(prefix="/audit-log", tags=["Auditoría"])

CompanyAdmin = Annotated[UserModel, Depends(require_company_admin)]


@router.get("/", response_model=list[AuditLogResponse], summary="Ver log de auditoría")
async def list_audit_log(
    current_user: CompanyAdmin,
    x_active_tenant: Optional[str] = Header(default=None, alias="X-Active-Tenant"),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 25,
    user_id: Optional[UUID] = Query(None),
    document_id: Optional[UUID] = Query(None),
    action: Optional[AuditAction] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
) -> list[dict]:
    """
    Lista el log de auditoría enriquecido con nombre de usuario y nombre de documento.
    - Admin de empresa: solo su organización.
    - Super admin con X-Active-Tenant: la empresa indicada.
    - Super admin sin X-Active-Tenant: log global de todas las organizaciones.
    """
    q = (
        db.query(AuditLog)
        .options(
            joinedload(AuditLog.user),
            joinedload(AuditLog.document),
        )
    )

    is_super = current_user.role.value == "super_admin"

    if not is_super:
        org_user_ids = (
            db.query(UserModel.id)
            .filter(UserModel.organization_id == current_user.organization_id)
            .scalar_subquery()
        )
        q = q.filter(AuditLog.user_id.in_(org_user_ids))
    elif x_active_tenant:
        try:
            tenant_uuid = UUID(x_active_tenant)
            org_user_ids = (
                db.query(UserModel.id)
                .filter(UserModel.organization_id == tenant_uuid)
                .scalar_subquery()
            )
            q = q.filter(AuditLog.user_id.in_(org_user_ids))
        except ValueError:
            pass
    # else: super admin global → sin filtro de org

    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if document_id:
        q = q.filter(AuditLog.document_id == document_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if from_date:
        q = q.filter(AuditLog.timestamp >= from_date)
    if to_date:
        # Incluir todo el día final
        q = q.filter(AuditLog.timestamp <= to_date)

    entries = q.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

    # Enriquecer con nombres resueltos desde las relaciones
    return [
        {
            "id": e.id,
            "document_id": e.document_id,
            "document_name": e.document.original_filename if e.document else None,
            "user_id": e.user_id,
            "user_name": e.user.name if e.user else None,
            "user_email": e.user.email if e.user else None,
            "action": e.action,
            "detail_json": e.detail_json,
            "ip_address": e.ip_address,
            "timestamp": e.timestamp,
        }
        for e in entries
    ]
