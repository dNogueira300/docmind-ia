"""CRUD de organizaciones (tenants) — solo super_admin."""
from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_super_admin
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.category import Category
from app.models.document import Document
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationStats, OrganizationPublic, CreateAdminInOrg,
)

router = APIRouter(prefix="/organizations", tags=["Organizaciones"])

SuperAdmin = Annotated[User, Depends(require_super_admin)]


# ── Endpoint público para resolver tenant en la pantalla de login ────────────


@router.get(
    "/by-slug/{slug}",
    response_model=OrganizationPublic,
    summary="Resolver organización por slug (público)",
)
async def get_organization_by_slug(
    slug: str,
    db: Session = Depends(get_db),
) -> Organization:
    """
    Sin autenticación. Devuelve datos públicos (nombre + slug + active)
    para que la página de login pueda mostrar a qué empresa el usuario
    está accediendo. Si no existe o está inactiva → 404.
    """
    org = db.query(Organization).filter(Organization.slug == slug.lower()).first()
    if org is None or not org.active:
        raise HTTPException(status_code=404, detail="Empresa no encontrada o inactiva")
    return org


# ── CRUD de organizaciones (super_admin) ─────────────────────────────────────


@router.get("/", response_model=list[OrganizationResponse], summary="Listar empresas")
async def list_organizations(
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    include_inactive: bool = False,
) -> list[Organization]:
    q = db.query(Organization)
    if not include_inactive:
        q = q.filter(Organization.active.is_(True))
    return q.order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()


@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=201,
    summary="Crear empresa (opcionalmente con su admin inicial)",
)
async def create_organization(
    data: OrganizationCreate,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> Organization:
    # Slug único
    existing = db.query(Organization).filter(Organization.slug == data.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El slug '{data.slug}' ya está en uso por otra empresa",
        )

    org = Organization(name=data.name, slug=data.slug, active=True)
    db.add(org)
    db.flush()  # para conseguir org.id sin commit aún

    # Si vienen datos del admin, crearlo en la misma transacción
    if data.admin_email and data.admin_password:
        admin = User(
            organization_id=org.id,
            name=data.admin_name or data.admin_email.split("@")[0],
            email=data.admin_email,
            password_hash=hash_password(data.admin_password),
            role=UserRole.admin,
            active=True,
        )
        db.add(admin)

    db.commit()
    db.refresh(org)
    return org


@router.put(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Editar empresa (nombre / slug / activación)",
)
async def update_organization(
    organization_id: UUID,
    data: OrganizationUpdate,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> Organization:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if data.slug and data.slug != org.slug:
        clash = db.query(Organization).filter(Organization.slug == data.slug).first()
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El slug '{data.slug}' ya está en uso",
            )
        org.slug = data.slug

    if data.name is not None:
        org.name = data.name
    if data.active is not None:
        org.active = data.active

    db.commit()
    db.refresh(org)
    return org


@router.delete("/{organization_id}", summary="Desactivar empresa (no destruye datos)")
async def deactivate_organization(
    organization_id: UUID,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> dict:
    """
    Desactiva la empresa. Los datos NO se eliminan: los documentos quedan en
    MinIO y la BD; los usuarios no podrán iniciar sesión hasta reactivarla.
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    org.active = False
    db.commit()
    return {"detail": f"Empresa '{org.name}' desactivada"}


@router.get(
    "/stats",
    response_model=list[OrganizationStats],
    summary="Estadísticas globales por empresa",
)
async def organizations_stats(
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> list[OrganizationStats]:
    """Métricas agregadas (cantidad de usuarios, categorías, documentos, storage)."""
    rows = (
        db.query(
            Organization.id,
            Organization.name,
            Organization.slug,
            Organization.active,
            func.count(func.distinct(User.id)).label("users_count"),
            func.count(func.distinct(Category.id)).label("categories_count"),
            func.count(func.distinct(Document.id)).label("documents_count"),
            func.coalesce(func.sum(Document.file_size_kb), 0).label("storage_kb"),
        )
        .outerjoin(User, User.organization_id == Organization.id)
        .outerjoin(Category, Category.organization_id == Organization.id)
        .outerjoin(Document, Document.organization_id == Organization.id)
        .group_by(Organization.id)
        .order_by(Organization.name)
        .all()
    )
    return [
        OrganizationStats(
            id=r.id, name=r.name, slug=r.slug, active=r.active,
            users_count=r.users_count or 0,
            categories_count=r.categories_count or 0,
            documents_count=r.documents_count or 0,
            storage_kb=int(r.storage_kb or 0),
        )
        for r in rows
    ]


@router.post(
    "/{organization_id}/admin",
    status_code=201,
    summary="Crear administrador principal en una empresa",
)
async def create_admin_in_organization(
    organization_id: UUID,
    data: CreateAdminInOrg,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> dict:
    """
    Da de alta un usuario con rol `admin` en la empresa indicada.
    Útil cuando se crea una empresa primero y se asigna el admin después,
    o para añadir un admin adicional.
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    clash = (
        db.query(User)
        .filter(User.organization_id == organization_id, User.email == data.email)
        .first()
    )
    if clash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un usuario con email '{data.email}' en esta empresa",
        )

    admin = User(
        organization_id=organization_id,
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.admin,
        active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return {
        "detail": f"Admin '{admin.email}' creado en empresa '{org.name}'",
        "id": str(admin.id),
    }
