"""CRUD de organizaciones (tenants) — solo super_admin."""
import secrets
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    require_super_admin, require_company_admin, get_current_user,
    get_active_organization_id,
)
from app.core.security import hash_password
from app.core.plans import Plan, normalize_plan
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.category import Category
from app.models.document import Document
from app.models.activation_code import ActivationCode
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationStats, OrganizationPublic, CreateAdminInOrg,
    ActivateCodeRequest, ActivationCodeCreate, ActivationCodeResponse,
)
from app.services import plan_service

router = APIRouter(prefix="/organizations", tags=["Organizaciones"])

SuperAdmin = Annotated[User, Depends(require_super_admin)]
CompanyAdmin = Annotated[User, Depends(require_company_admin)]
AnyRole = Annotated[User, Depends(get_current_user)]


def _generate_code() -> str:
    """Genera un código tipo DOCMIND-XXXX-XXXX (legible, sin caracteres ambiguos)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    part = lambda: "".join(secrets.choice(alphabet) for _ in range(4))
    return f"DOCMIND-{part()}-{part()}"


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


# ── Plan y activación (admin de empresa) ─────────────────────────────────────


@router.get("/plan", summary="Plan, límites y uso de la empresa activa")
async def get_plan(
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """Devuelve el plan vigente, sus límites/features y el uso actual."""
    org = plan_service.get_org(db, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return plan_service.plan_overview(db, org)


@router.post("/activate", summary="Canjear código de activación → activa el plan")
async def activate_plan(
    body: ActivateCodeRequest,
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """El admin de la empresa canjea un código y activa el plan correspondiente."""
    code = (body.code or "").strip().upper()
    ac = db.query(ActivationCode).filter(ActivationCode.code == code).first()
    if ac is None:
        raise HTTPException(status_code=404, detail="Código de activación inválido")
    if ac.used:
        raise HTTPException(status_code=409, detail="Este código ya fue utilizado")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if ac.expires_at and ac.expires_at < now:
        raise HTTPException(status_code=409, detail="El código de activación expiró")

    org = plan_service.get_org(db, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    org.plan = normalize_plan(ac.plan).value
    org.plan_expires_at = now + timedelta(days=ac.duration_days)
    # Reiniciar la ventana de créditos al activar.
    org.ai_credits_used = 0
    org.ai_credits_reset_at = now + timedelta(days=30)

    ac.used = True
    ac.used_by_org = org.id
    ac.used_at = now
    db.commit()

    return {
        "detail": f"Plan '{org.plan}' activado hasta {org.plan_expires_at:%Y-%m-%d}",
        "plan": org.plan,
        "plan_expires_at": org.plan_expires_at.isoformat(),
    }


# ── Generación de códigos (super_admin) ──────────────────────────────────────


@router.post(
    "/activation-codes",
    response_model=list[ActivationCodeResponse],
    status_code=201,
    summary="Generar código(s) de activación (super_admin)",
)
async def create_activation_codes(
    data: ActivationCodeCreate,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> list[ActivationCode]:
    plan = normalize_plan(data.plan)
    if plan == Plan.free:
        raise HTTPException(
            status_code=422, detail="No tiene sentido un código para el plan gratuito"
        )
    qty = max(1, min(data.quantity, 100))
    codes: list[ActivationCode] = []
    for _ in range(qty):
        code = _generate_code()
        while db.query(ActivationCode).filter(ActivationCode.code == code).first():
            code = _generate_code()
        ac = ActivationCode(
            code=code, plan=plan.value, duration_days=data.duration_days
        )
        db.add(ac)
        codes.append(ac)
    db.commit()
    for ac in codes:
        db.refresh(ac)
    return codes


@router.get(
    "/activation-codes",
    response_model=list[ActivationCodeResponse],
    summary="Listar códigos de activación (super_admin)",
)
async def list_activation_codes(
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
    only_unused: bool = False,
) -> list[ActivationCode]:
    q = db.query(ActivationCode)
    if only_unused:
        q = q.filter(ActivationCode.used.is_(False))
    return q.order_by(ActivationCode.created_at.desc()).limit(200).all()


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
