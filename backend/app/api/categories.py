"""CRUD de categorías — personalizables por organización."""
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role, get_current_user
from app.models.user import User
from app.models.category import Category
from app.models.document import Document
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categorías"])

AdminOnly = Annotated[User, Depends(require_role("admin"))]
AnyRole = Annotated[User, Depends(get_current_user)]


@router.get("/", response_model=list[CategoryResponse], summary="Listar categorías")
async def list_categories(
    current_user: AnyRole,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
) -> list[Category]:
    """Lista las categorías de la organización del usuario."""
    return (
        db.query(Category)
        .filter(Category.organization_id == current_user.organization_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post(
    "/", response_model=CategoryResponse, status_code=201, summary="Crear categoría"
)
async def create_category(
    data: CategoryCreate,
    current_user: AdminOnly,
    db: Session = Depends(get_db),
) -> Category:
    """Crea una nueva categoría. Máximo 10 por organización (prototipo)."""
    total = (
        db.query(Category)
        .filter(Category.organization_id == current_user.organization_id)
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
            Category.organization_id == current_user.organization_id,
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
        organization_id=current_user.organization_id,
        name=data.name,
        description=data.description,
        color=data.color,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse, summary="Editar categoría")
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    current_user: AdminOnly,
    db: Session = Depends(get_db),
) -> Category:
    """Edita nombre, descripción o color de una categoría."""
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.organization_id == current_user.organization_id,
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

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", summary="Eliminar categoría")
async def delete_category(
    category_id: UUID,
    current_user: AdminOnly,
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
            Category.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    # Desvincular documentos (category_id → NULL)
    db.query(Document).filter(Document.category_id == category_id).update(
        {"category_id": None}
    )

    db.delete(category)
    db.commit()
    return {"detail": f"Categoría '{category.name}' eliminada. Documentos movidos a 'Sin categoría'."}
