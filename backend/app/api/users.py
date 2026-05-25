"""CRUD de usuarios — aislado por tenant; admins solo ven a su propia empresa."""
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_company_admin, get_active_organization_id
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["Usuarios"])

# admin de la empresa O super_admin (cuando opera vía X-Active-Tenant).
CompanyAdmin = Annotated[User, Depends(require_company_admin)]


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
