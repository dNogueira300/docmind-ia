"""CRUD de categorías — aisladas por tenant (multi-tenant)."""
from datetime import datetime, timezone
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    require_role, get_current_user, get_active_organization_id,
    require_company_admin,
)
from app.models.user import User
from app.models.category import Category
from app.models.category_suggestion import CategorySuggestion, SuggestionStatus
from app.models.document import Document, DocStatus
from app.models.audit_log import AuditAction
from app.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategorySuggestionResponse,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/categories", tags=["Categorías"])

# `admin` (de la empresa) y `super_admin` (operando vía X-Active-Tenant)
CompanyAdmin = Annotated[User, Depends(require_company_admin)]
AnyRole = Annotated[User, Depends(get_current_user)]


@router.get("/", response_model=list[CategoryResponse], summary="Listar categorías")
async def list_categories(
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
) -> list[Category]:
    """Lista las categorías de la empresa activa."""
    return (
        db.query(Category)
        .filter(Category.organization_id == organization_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post(
    "/", response_model=CategoryResponse, status_code=201, summary="Crear categoría"
)
async def create_category(
    data: CategoryCreate,
    request: Request,
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> Category:
    """Crea una nueva categoría en la empresa activa. Máximo 10 por organización."""
    total = (
        db.query(Category)
        .filter(Category.organization_id == organization_id)
        .count()
    )
    if total >= 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Límite de 10 categorías por organización alcanzado",
        )

    existing = (
        db.query(Category)
        .filter(
            Category.organization_id == organization_id,
            Category.name == data.name,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe la categoría '{data.name}'",
        )

    category = Category(
        organization_id=organization_id,
        name=data.name,
        description=data.description,
        color=data.color,
        requires_approval=data.requires_approval,
        approver_role=data.approver_role,
    )
    db.add(category)
    db.commit()
    db.refresh(category)

    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.category_create,
        detail={"category_id": str(category.id), "name": category.name},
        ip_address=request.client.host if request.client else None,
    )
    return category


# ── Sugerencias de categorías (propuestas por la IA) ──────────────────────────

@router.get(
    "/suggestions",
    response_model=list[CategorySuggestionResponse],
    summary="Listar sugerencias de categorías de la IA",
)
async def list_category_suggestions(
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
    status_filter: str = "pending",
) -> list[dict]:
    """Lista las sugerencias de categorías (por defecto solo las pendientes),
    incluyendo el nombre del documento que originó cada una."""
    query = (
        db.query(CategorySuggestion, Document.original_filename)
        .outerjoin(Document, Document.id == CategorySuggestion.document_id)
        .filter(CategorySuggestion.organization_id == organization_id)
    )
    if status_filter:
        query = query.filter(CategorySuggestion.status == status_filter)
    rows = query.order_by(CategorySuggestion.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "organization_id": s.organization_id,
            "document_id": s.document_id,
            "document_name": doc_name,
            "suggested_name": s.suggested_name,
            "confidence": s.confidence,
            "status": s.status.value if hasattr(s.status, "value") else s.status,
            "created_at": s.created_at,
        }
        for s, doc_name in rows
    ]


@router.post(
    "/suggestions/{suggestion_id}/approve",
    response_model=CategoryResponse,
    summary="Aprobar sugerencia → crea la categoría",
)
async def approve_category_suggestion(
    suggestion_id: UUID,
    request: Request,
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> Category:
    """Aprueba una sugerencia: crea la categoría (respetando el límite de 10) y
    marca la sugerencia como aprobada."""
    suggestion = (
        db.query(CategorySuggestion)
        .filter(
            CategorySuggestion.id == suggestion_id,
            CategorySuggestion.organization_id == organization_id,
        )
        .first()
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Sugerencia no encontrada")
    if suggestion.status != SuggestionStatus.pending:
        raise HTTPException(status_code=409, detail="La sugerencia ya fue procesada")

    # Categoría destino: la existente con ese nombre, o una nueva.
    category = (
        db.query(Category)
        .filter(
            Category.organization_id == organization_id,
            func.lower(Category.name) == suggestion.suggested_name.lower(),
        )
        .first()
    )
    created = False
    if category is None:
        total = (
            db.query(Category)
            .filter(Category.organization_id == organization_id)
            .count()
        )
        if total >= 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Límite de 10 categorías por organización alcanzado",
            )
        category = Category(
            organization_id=organization_id,
            name=suggestion.suggested_name,
            description="Categoría sugerida por la IA",
        )
        db.add(category)
        db.flush()  # asignar id sin cerrar la transacción
        created = True

    # Auto-clasificar el documento que originó la sugerencia: si sigue en review
    # y sin categoría, queda clasificado en la categoría recién aprobada.
    if suggestion.document_id:
        src_doc = (
            db.query(Document)
            .filter(
                Document.id == suggestion.document_id,
                Document.organization_id == organization_id,
            )
            .first()
        )
        if src_doc and src_doc.category_id is None and src_doc.status == DocStatus.review:
            src_doc.category_id = category.id
            src_doc.status = DocStatus.classified
            if src_doc.ai_confidence_score is None:
                src_doc.ai_confidence_score = suggestion.confidence
            src_doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    suggestion.status = SuggestionStatus.approved
    suggestion.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    suggestion.reviewed_by = current_user.id
    db.commit()
    db.refresh(category)

    if created:
        log_action(
            db=db,
            user_id=current_user.id,
            action=AuditAction.category_create,
            detail={
                "category_id": str(category.id),
                "name": category.name,
                "source": "ai_suggestion",
            },
            ip_address=request.client.host if request.client else None,
        )
    return category


@router.post(
    "/suggestions/{suggestion_id}/reject",
    summary="Rechazar sugerencia de categoría",
)
async def reject_category_suggestion(
    suggestion_id: UUID,
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    suggestion = (
        db.query(CategorySuggestion)
        .filter(
            CategorySuggestion.id == suggestion_id,
            CategorySuggestion.organization_id == organization_id,
        )
        .first()
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Sugerencia no encontrada")
    if suggestion.status != SuggestionStatus.pending:
        raise HTTPException(status_code=409, detail="La sugerencia ya fue procesada")

    suggestion.status = SuggestionStatus.rejected
    suggestion.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    suggestion.reviewed_by = current_user.id
    db.commit()
    return {"detail": "Sugerencia rechazada"}


@router.put("/{category_id}", response_model=CategoryResponse, summary="Editar categoría")
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    request: Request,
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> Category:
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.organization_id == organization_id,
        )
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    if data.name is not None:
        category.name = data.name
    if data.description is not None:
        category.description = data.description
    if data.color is not None:
        category.color = data.color
    if data.requires_approval is not None:
        category.requires_approval = data.requires_approval
    if data.approver_role is not None:
        category.approver_role = data.approver_role

    db.commit()
    db.refresh(category)

    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.category_update,
        detail={"category_id": str(category_id), "name": category.name},
        ip_address=request.client.host if request.client else None,
    )
    return category


@router.delete("/{category_id}", summary="Eliminar categoría")
async def delete_category(
    category_id: UUID,
    request: Request,
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """
    Elimina una categoría.
    Los documentos asociados pasan a category_id = NULL (no se eliminan).
    """
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.organization_id == organization_id,
        )
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    category_name = category.name
    db.query(Document).filter(Document.category_id == category_id).update(
        {"category_id": None}
    )

    db.delete(category)
    db.commit()

    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.category_delete,
        detail={"category_id": str(category_id), "name": category_name},
        ip_address=request.client.host if request.client else None,
    )
    return {"detail": f"Categoría '{category_name}' eliminada. Documentos movidos a 'Sin categoría'."}
