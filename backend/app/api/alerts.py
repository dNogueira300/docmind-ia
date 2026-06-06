"""Endpoints de alertas de vencimiento."""
from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import require_role, get_active_organization_id
from app.models.user import User
from app.models.alert import DocumentAlert, AlertStatus, AlertType
from app.schemas.alert import AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alertas"])

EditorOrAdmin = Annotated[User, Depends(require_role("admin", "editor"))]


def _enrich(alert: DocumentAlert) -> dict:
    """Construye el dict de respuesta enriquecido con nombre del documento."""
    return {
        "id":              alert.id,
        "document_id":     alert.document_id,
        "document_name":   alert.document.original_filename if alert.document else None,
        "organization_id": alert.organization_id,
        "alert_type":      alert.alert_type,
        "detected_date":   alert.detected_date,
        "alert_date":      alert.alert_date,
        "status":          alert.status,
        "detail":          alert.detail,
        "created_at":      alert.created_at,
    }


@router.get("/", response_model=list[AlertResponse], summary="Listar alertas de vencimiento")
async def list_alerts(
    current_user: EditorOrAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
    status: Optional[AlertStatus] = Query(None),
    alert_type: Optional[AlertType] = Query(None),
    document_id: Optional[UUID] = Query(None),
    skip: int = 0,
    limit: int = 50,
) -> list[dict]:
    q = (
        db.query(DocumentAlert)
        .options(joinedload(DocumentAlert.document))
        .filter(DocumentAlert.organization_id == organization_id)
    )
    if status:
        q = q.filter(DocumentAlert.status == status)
    if alert_type:
        q = q.filter(DocumentAlert.alert_type == alert_type)
    if document_id:
        q = q.filter(DocumentAlert.document_id == document_id)

    alerts = q.order_by(DocumentAlert.alert_date.asc()).offset(skip).limit(limit).all()
    return [_enrich(a) for a in alerts]


@router.patch("/{alert_id}/dismiss", response_model=AlertResponse, summary="Marcar alerta como revisada")
async def dismiss_alert(
    alert_id: UUID,
    current_user: EditorOrAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    alert = (
        db.query(DocumentAlert)
        .options(joinedload(DocumentAlert.document))
        .filter(
            DocumentAlert.id == alert_id,
            DocumentAlert.organization_id == organization_id,
        )
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    alert.status = AlertStatus.dismissed
    db.commit()
    db.refresh(alert)
    return _enrich(alert)
