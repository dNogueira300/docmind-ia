"""Endpoints de autenticación: login y logout."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.user import User
from app.models.audit_log import AuditAction
from app.schemas.token import Token
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=Token, summary="Iniciar sesión")
@limiter.limit("10/minute", error_message="Demasiados intentos. Espera un minuto antes de intentar de nuevo.")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Autentica un usuario y retorna un JWT válido por 8 horas."""
    user = (
        db.query(User)
        .filter(User.email == form_data.username)
        .first()
    )
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está desactivada",
        )

    token = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role.value,
        email=user.email,
    )

    # Registrar login en auditoría
    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=user.id,
        action=AuditAction.login,
        detail={"email": user.email},
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
async def get_me(current_user: User = Depends(get_current_user)) -> dict:
    """Retorna los datos del usuario autenticado."""
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value,
        "organization_id": str(current_user.organization_id),
        "active": current_user.active,
    }
