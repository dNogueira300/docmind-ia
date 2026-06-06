"""Endpoint de chatbot — documental y global — usa Google Gemini como motor.

IMPORTANTE: /global debe declararse ANTES que /{document_id} para que FastAPI
no intente parsear la cadena "global" como UUID y devuelva 422.
"""
from uuid import UUID
from typing import Annotated
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_active_organization_id
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.models.alert import DocumentAlert, AlertStatus
from app.models.approval import DocumentApproval, ApprovalStatus
from app.services import gemini_service

router = APIRouter(prefix="/chat", tags=["Chatbot"])

AnyRole = Annotated[User, Depends(get_current_user)]


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    history: list[dict]


# ── /global PRIMERO — evita que "global" sea interpretado como document_id ────

@router.post(
    "/global",
    response_model=ChatResponse,
    summary="Chatbot global del sistema",
)
async def global_chat(
    body: ChatRequest,
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """Reúne estadísticas de la organización y responde preguntas sobre el sistema."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    # Estadísticas del sistema
    total_docs = db.query(func.count(Document.id)).filter(
        Document.organization_id == organization_id
    ).scalar() or 0

    by_status = dict(
        db.query(Document.status, func.count(Document.id))
        .filter(Document.organization_id == organization_id)
        .group_by(Document.status).all()
    )

    by_category = db.query(
        Category.name, func.count(Document.id).label("count")
    ).outerjoin(
        Document,
        (Document.category_id == Category.id) & (Document.organization_id == organization_id)
    ).filter(Category.organization_id == organization_id).group_by(Category.name).all()

    from app.models.user import User as UserModel  # noqa: PLC0415
    top_users = db.query(
        UserModel.name, func.count(Document.id).label("count")
    ).join(Document, Document.uploaded_by == UserModel.id).filter(
        Document.organization_id == organization_id
    ).group_by(UserModel.name).order_by(func.count(Document.id).desc()).limit(5).all()

    recent = db.query(
        Document.original_filename, Document.status, Document.created_at
    ).filter(Document.organization_id == organization_id).order_by(
        Document.created_at.desc()
    ).limit(5).all()

    pending_alerts = db.query(func.count(DocumentAlert.id)).filter(
        DocumentAlert.organization_id == organization_id,
        DocumentAlert.status == AlertStatus.pending,
    ).scalar() or 0

    pending_approvals = db.query(func.count(DocumentApproval.id)).filter(
        DocumentApproval.organization_id == organization_id,
        DocumentApproval.status == ApprovalStatus.pending,
    ).scalar() or 0

    context = {
        "fecha_actual": datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M UTC"),
        "total_documentos": total_docs,
        "documentos_por_estado": {
            (k.value if hasattr(k, "value") else str(k)): v
            for k, v in by_status.items()
        },
        "documentos_por_categoria": [
            {"categoria": r.name, "cantidad": r.count} for r in by_category
        ],
        "top_usuarios_por_subidas": [
            {"usuario": r.name, "documentos": r.count} for r in top_users
        ],
        "ultimos_documentos": [
            {
                "nombre": r.original_filename,
                "estado": r.status.value if hasattr(r.status, "value") else str(r.status),
                "fecha": str(r.created_at)[:10],
            }
            for r in recent
        ],
        "alertas_pendientes": pending_alerts,
        "aprobaciones_pendientes": pending_approvals,
    }

    reply = gemini_service.chat_global(
        message=body.message.strip(),
        context=context,
        history=body.history,
    )

    return {
        "reply": reply,
        "history": [
            *body.history,
            {"role": "user",      "content": body.message.strip()},
            {"role": "assistant", "content": reply},
        ],
    }


# ── /{document_id} DESPUÉS — FastAPI solo llega aquí si no fue /global ────────

@router.post(
    "/{document_id}",
    response_model=ChatResponse,
    summary="Chatbot documental — pregunta sobre un documento específico",
)
async def chat_with_document(
    document_id: UUID,
    body: ChatRequest,
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """Responde preguntas sobre el contenido OCR de un documento."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.organization_id == organization_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    reply = (
        "Este documento aún no ha sido procesado por OCR o no tiene texto extraíble. "
        "Reprocésalo desde el menú contextual."
        if not doc.ocr_text
        else gemini_service.chat(
            message=body.message.strip(),
            doc_text=doc.ocr_text,
            doc_name=doc.original_filename,
            history=body.history,
        )
    )

    return {
        "reply": reply,
        "history": [
            *body.history,
            {"role": "user",      "content": body.message.strip()},
            {"role": "assistant", "content": reply},
        ],
    }
