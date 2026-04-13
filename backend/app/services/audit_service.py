"""Servicio de auditoría — registra operaciones sobre documentos."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog, AuditAction


def log_action(
    db: Session,
    user_id: UUID,
    action: AuditAction,
    document_id: Optional[UUID] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Inserta una entrada en audit_log.

    La tabla audit_log es INMUTABLE: nunca se emiten UPDATE ni DELETE sobre ella.
    """
    entry = AuditLog(
        document_id=document_id,
        user_id=user_id,
        action=action,
        detail_json=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
