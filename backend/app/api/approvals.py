"""Endpoints de flujos de aprobación documental."""
from datetime import datetime, timezone
from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role, get_active_organization_id
from app.models.user import User
from app.models.approval import DocumentApproval, ApprovalStatus
from app.models.document import Document, DocStatus
from app.models.audit_log import AuditAction
from app.schemas.approval import ApprovalResponse, ApprovalAction
from app.services.audit_service import log_action

router = APIRouter(prefix="/approvals", tags=["Aprobaciones"])

EditorOrAdmin = Annotated[User, Depends(require_role("admin", "editor"))]


@router.get("/", response_model=list[ApprovalResponse], summary="Listar aprobaciones pendientes")
async def list_approvals(
    current_user: EditorOrAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
    status: Optional[ApprovalStatus] = Query(None, description="Filtrar por estado"),
    skip: int = 0,
    limit: int = 20,
) -> list[DocumentApproval]:
    q = db.query(DocumentApproval).filter(
        DocumentApproval.organization_id == organization_id
    )
    if status:
        q = q.filter(DocumentApproval.status == status)
    return q.order_by(DocumentApproval.requested_at.desc()).offset(skip).limit(limit).all()


@router.post(
    "/{document_id}/approve",
    response_model=ApprovalResponse,
    summary="Aprobar documento",
)
async def approve_document(
    document_id: UUID,
    data: ApprovalAction,
    request: Request,
    current_user: EditorOrAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> DocumentApproval:
    approval = _get_pending_approval(db, document_id, organization_id)

    approval.status = ApprovalStatus.approved
    approval.reviewed_by = current_user.id
    approval.comment = data.comment
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        doc.status = DocStatus.classified
        doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.commit()
    db.refresh(approval)

    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.reclassify,
        document_id=document_id,
        detail={"action": "approved", "comment": data.comment},
        ip_address=ip,
    )
    return approval


@router.post(
    "/{document_id}/reject",
    response_model=ApprovalResponse,
    summary="Rechazar documento",
)
async def reject_document(
    document_id: UUID,
    data: ApprovalAction,
    request: Request,
    current_user: EditorOrAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> DocumentApproval:
    approval = _get_pending_approval(db, document_id, organization_id)

    approval.status = ApprovalStatus.rejected
    approval.reviewed_by = current_user.id
    approval.comment = data.comment
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        doc.status = DocStatus.review
        doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.commit()
    db.refresh(approval)

    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.reclassify,
        document_id=document_id,
        detail={"action": "rejected", "comment": data.comment},
        ip_address=ip,
    )
    return approval


def _get_pending_approval(
    db: Session, document_id: UUID, organization_id: UUID
) -> DocumentApproval:
    approval = (
        db.query(DocumentApproval)
        .filter(
            DocumentApproval.document_id == document_id,
            DocumentApproval.organization_id == organization_id,
            DocumentApproval.status == ApprovalStatus.pending,
        )
        .first()
    )
    if not approval:
        raise HTTPException(
            status_code=404,
            detail="No hay una solicitud de aprobación pendiente para este documento",
        )
    return approval
