"""Endpoints de autenticación: login, logout, /me."""
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.audit_log import AuditAction
from app.schemas.token import Token
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=Token, summary="Iniciar sesión")
@limiter.limit("10/minute", error_message="Demasiados intentos. Espera un minuto antes de intentar de nuevo.")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    org_slug: Optional[str] = Form(default=None, description="Slug de la empresa (obligatorio para usuarios regulares)"),
    db: Session = Depends(get_db),
) -> Token:
    """
    Autentica un usuario y retorna un JWT válido por 8 horas.

    Reglas multi-tenant:
      - Usuario regular (admin/editor/consultor): DEBE enviar `org_slug` para
        identificar a qué empresa pertenece. Sin él, se asume "el primero
        encontrado" lo cual permitiría colisiones de email entre empresas.
      - `super_admin`: no necesita `org_slug` (existe único en el sistema).

    Devuelve 401 si: email/password incorrectos, usuario inactivo o empresa
    inactiva/no encontrada.
    """
    email = form_data.username

    # 1) Resolver candidatos por email
    candidates = db.query(User).filter(User.email == email).all()
    if not candidates:
        _unauthorized()

    # 2) Si vino org_slug, filtrar a esa empresa
    if org_slug:
        org = (
            db.query(Organization)
            .filter(Organization.slug == org_slug.lower())
            .first()
        )
        if not org:
            _unauthorized()
        if not org.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La empresa está desactivada. Contacta al super administrador.",
            )
        candidates = [u for u in candidates if u.organization_id == org.id]
        if not candidates:
            _unauthorized()
    else:
        # Sin org_slug → solo permitir si todos los candidatos son super_admin
        non_super = [u for u in candidates if u.role.value != "super_admin"]
        if non_super:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Debes indicar la empresa (org_slug) para iniciar sesión. "
                    "Si eres super administrador, este endpoint no requiere slug."
                ),
            )

    # 3) Verificar password (probamos cada candidato hasta encontrar uno válido)
    user = next(
        (u for u in candidates if verify_password(form_data.password, u.password_hash)),
        None,
    )
    if not user:
        _unauthorized()

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está desactivada",
        )

    token = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,  # puede ser None para super_admin
        role=user.role.value,
        email=user.email,
    )

    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=user.id,
        action=AuditAction.login,
        detail={"email": user.email, "org_slug": org_slug},
        ip_address=ip,
    )

    return Token(access_token=token)


@router.post("/logout", summary="Cerrar sesión")
async def logout(current_user: User = Depends(get_current_user)) -> dict:
    """
    Cierra la sesión del usuario.
    El token JWT es stateless; el cliente debe descartarlo.
    """
    return {"detail": "Sesión cerrada correctamente"}


@router.get("/me", summary="Usuario actual")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Retorna los datos del usuario autenticado, incluyendo su empresa."""
    org_payload = None
    if current_user.organization_id is not None:
        org = (
            db.query(Organization)
            .filter(Organization.id == current_user.organization_id)
            .first()
        )
        if org:
            org_payload = {
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug,
                "active": org.active,
            }

    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value,
        "organization_id": (
            str(current_user.organization_id)
            if current_user.organization_id else None
        ),
        "organization": org_payload,
        "active": current_user.active,
        "is_super_admin": current_user.role.value == "super_admin",
    }


def _unauthorized() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email o contraseña incorrectos",
        headers={"WWW-Authenticate": "Bearer"},
    )
