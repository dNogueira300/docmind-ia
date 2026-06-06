"""CRUD de usuarios — aislado por tenant; admins solo ven a su propia empresa."""
from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import require_company_admin, require_super_admin, get_active_organization_id
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.audit_log import AuditAction
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse,
    GlobalAdminCreate, GlobalAdminUpdate, GlobalAdminPasswordUpdate, GlobalAdminResponse,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/users", tags=["Usuarios"])

# admin de la empresa O super_admin (cuando opera vía X-Active-Tenant).
CompanyAdmin = Annotated[User, Depends(require_company_admin)]
SuperAdmin = Annotated[User, Depends(require_super_admin)]


@router.get(
    "/global-admins",
    response_model=list[GlobalAdminResponse],
    summary="Listar admins de todas las empresas (solo super_admin)",
)
async def list_global_admins(
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """Retorna todos los usuarios con rol 'admin' de cualquier organización, con nombre de empresa."""
    users = (
        db.query(User)
        .options(joinedload(User.organization))
        .filter(User.role == UserRole.admin)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": u.id,
            "organization_id": u.organization_id,
            "organization_name": u.organization.name if u.organization else None,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "active": u.active,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.post(
    "/global-admins",
    response_model=GlobalAdminResponse,
    status_code=201,
    summary="Crear admin en cualquier empresa (solo super_admin)",
)
async def create_global_admin(
    request: Request,
    data: GlobalAdminCreate,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> dict:
    """Crea un usuario admin en la organización indicada."""
    org = db.query(Organization).filter(Organization.id == data.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organización no encontrada")
    if not org.active:
        raise HTTPException(status_code=400, detail="La organización está desactivada")

    existing = (
        db.query(User)
        .filter(User.organization_id == data.organization_id, User.email == data.email)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un usuario con el email '{data.email}' en esa empresa",
        )

    user = User(
        organization_id=data.organization_id,
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.admin,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.user_create,
        detail={
            "created_user_id": str(user.id),
            "created_user_name": user.name,
            "created_user_email": user.email,
            "organization": org.name,
        },
        ip_address=ip,
    )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    return {
        "id": user.id,
        "organization_id": user.organization_id,
        "organization_name": org.name if org else None,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "created_at": user.created_at,
    }


@router.put(
    "/global-admins/{user_id}",
    response_model=GlobalAdminResponse,
    summary="Editar admin (solo super_admin)",
)
async def update_global_admin(
    user_id: UUID,
    request: Request,
    data: GlobalAdminUpdate,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> dict:
    """Edita nombre y/o email de un usuario admin."""
    user = _get_admin_or_404(db, user_id)

    changes: dict = {}
    if data.name is not None and data.name != user.name:
        changes["name"] = {"from": user.name, "to": data.name}
        user.name = data.name
    if data.email is not None and data.email != user.email:
        duplicate = (
            db.query(User)
            .filter(
                User.organization_id == user.organization_id,
                User.email == data.email,
                User.id != user_id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El email '{data.email}' ya está en uso en esa empresa",
            )
        changes["email"] = {"from": user.email, "to": data.email}
        user.email = data.email

    db.commit()
    db.refresh(user)

    if changes:
        ip = request.client.host if request.client else None
        log_action(
            db=db,
            user_id=current_user.id,
            action=AuditAction.user_update,
            detail={
                "affected_user_id": str(user_id),
                "affected_user_name": user.name,
                "changes": changes,
            },
            ip_address=ip,
        )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    return {
        "id": user.id,
        "organization_id": user.organization_id,
        "organization_name": org.name if org else None,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "created_at": user.created_at,
    }


@router.patch(
    "/global-admins/{user_id}/password",
    summary="Cambiar contraseña de un admin (solo super_admin)",
)
async def change_global_admin_password(
    user_id: UUID,
    request: Request,
    data: GlobalAdminPasswordUpdate,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> dict:
    """Cambia la contraseña de un usuario admin."""
    user = _get_admin_or_404(db, user_id)
    user.password_hash = hash_password(data.new_password)
    db.commit()

    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.user_password,
        detail={
            "affected_user_id": str(user_id),
            "affected_user_name": user.name,
            "affected_user_email": user.email,
        },
        ip_address=ip,
    )

    return {"detail": f"Contraseña de '{user.name}' actualizada correctamente"}


@router.patch(
    "/global-admins/{user_id}/deactivate",
    response_model=GlobalAdminResponse,
    summary="Desactivar admin (solo super_admin)",
)
async def deactivate_global_admin(
    user_id: UUID,
    request: Request,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> dict:
    """Desactiva un usuario admin (no lo elimina)."""
    user = _get_admin_or_404(db, user_id)
    user.active = False
    db.commit()
    db.refresh(user)

    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.user_deactivate,
        detail={
            "affected_user_id": str(user_id),
            "affected_user_name": user.name,
            "affected_user_email": user.email,
        },
        ip_address=ip,
    )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    return {
        "id": user.id,
        "organization_id": user.organization_id,
        "organization_name": org.name if org else None,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "created_at": user.created_at,
    }


@router.patch(
    "/global-admins/{user_id}/activate",
    response_model=GlobalAdminResponse,
    summary="Reactivar admin (solo super_admin)",
)
async def activate_global_admin(
    user_id: UUID,
    request: Request,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> dict:
    """Reactiva un usuario admin que estaba desactivado."""
    user = _get_admin_or_404(db, user_id)
    user.active = True
    db.commit()
    db.refresh(user)

    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.user_activate,
        detail={
            "affected_user_id": str(user_id),
            "affected_user_name": user.name,
            "affected_user_email": user.email,
        },
        ip_address=ip,
    )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    return {
        "id": user.id,
        "organization_id": user.organization_id,
        "organization_name": org.name if org else None,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "created_at": user.created_at,
    }


def _get_admin_or_404(db: Session, user_id: UUID) -> User:
    """Obtiene un usuario con role='admin' o lanza 404."""
    user = (
        db.query(User)
        .filter(User.id == user_id, User.role == UserRole.admin)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Administrador no encontrado")
    return user


@router.get("/", response_model=list[UserResponse], summary="Listar usuarios")
async def list_users(
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
) -> list[User]:
    """Lista los usuarios de la empresa activa (nunca super_admins)."""
    return (
        db.query(User)
        .filter(
            User.organization_id == organization_id,
            User.role != UserRole.super_admin,
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/", response_model=UserResponse, status_code=201, summary="Crear usuario")
async def create_user(
    data: UserCreate,
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> User:
    """Crea un nuevo usuario en la empresa activa."""
    # Bloquear creación de super_admin desde aquí (solo via /organizations o seed)
    if data.role == UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se puede crear un super administrador desde este endpoint",
        )

    existing = (
        db.query(User)
        .filter(
            User.organization_id == organization_id,
            User.email == data.email,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un usuario con el email '{data.email}' en esta empresa",
        )

    user = User(
        organization_id=organization_id,
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="Editar usuario")
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> User:
    """Edita nombre, email, rol o estado activo de un usuario de la empresa activa."""
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.organization_id == organization_id,
            User.role != UserRole.super_admin,
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        if data.role == UserRole.super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No se puede asignar el rol super_admin desde este endpoint",
            )
        user.role = data.role
    if data.active is not None:
        user.active = data.active

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", summary="Desactivar usuario")
async def deactivate_user(
    user_id: UUID,
    current_user: CompanyAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """Desactiva un usuario de la empresa activa (no lo elimina de la BD)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta",
        )

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.organization_id == organization_id,
            User.role != UserRole.super_admin,
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.active = False
    db.commit()
    return {"detail": f"Usuario '{user.email}' desactivado correctamente"}
