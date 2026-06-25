"""Dependencias FastAPI reutilizables: autenticación, roles y resolución de tenant."""
from uuid import UUID
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
):
    """Decodifica el JWT y retorna el usuario activo. 401 si el token es inválido."""
    from app.models.user import User  # import tardío para evitar ciclos

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo o no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Si pertenece a una org, validar que la org esté activa.
    # super_admin no tiene org → se salta esta verificación.
    if user.organization_id is not None:
        from app.models.organization import Organization

        org = db.query(Organization).filter(
            Organization.id == user.organization_id
        ).first()
        if org is None or not org.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La empresa asociada a este usuario está inactiva o no existe",
            )

    return user


def require_role(*roles: str, allow_super_admin: bool = True):
    """
    Factoría que retorna una dependencia que exige uno de los roles dados.

    Por defecto, `super_admin` pasa siempre (es el rol global con permiso
    sobre todo). Si quieres restringir a roles de empresa exclusivamente,
    pasa `allow_super_admin=False`.
    """

    def guard(current_user=Depends(get_current_user)):
        if current_user.role.value == "super_admin" and allow_super_admin:
            return current_user
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes para esta acción",
            )
        return current_user

    return guard


def require_super_admin(current_user=Depends(get_current_user)):
    """Permite el paso solo a usuarios super_admin (rol global)."""
    if current_user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el super administrador puede realizar esta acción",
        )
    return current_user


def require_company_admin(current_user=Depends(get_current_user)):
    """
    Acceso para administradores de empresa (admin) y super admin.

    Útil para endpoints que un super_admin puede ejecutar dentro de cualquier
    tenant (debe enviar X-Active-Tenant) y que un admin puede ejecutar dentro
    de su propia empresa.
    """
    if current_user.role.value not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes para esta acción",
        )
    return current_user


# ── Resolución de tenant activo ──────────────────────────────────────────────


def get_active_organization_id(
    current_user=Depends(get_current_user),
    x_active_tenant: Optional[str] = Header(default=None, alias="X-Active-Tenant"),
    db: Session = Depends(get_db),
) -> UUID:
    """
    Devuelve el `organization_id` sobre el que el request opera.

    Reglas de aislamiento:
      - Usuario regular (admin/editor/consultor): SIEMPRE retorna
        `current_user.organization_id`. El header `X-Active-Tenant` se ignora,
        así un usuario nunca puede ver datos de otra empresa aunque manipule
        el header.
      - Super admin (organization_id IS NULL): DEBE enviar `X-Active-Tenant`
        con el UUID de la organización destino. Si lo omite, 400.

    Esta dependencia es la pieza clave del aislamiento multi-tenant: todos los
    endpoints "de empresa" deben pedirla en lugar de leer directamente
    `current_user.organization_id`.
    """
    from app.models.organization import Organization

    # Usuario regular: tenant fijo en su token, header ignorado.
    if current_user.organization_id is not None:
        return current_user.organization_id

    # Super admin: necesita declarar sobre qué tenant opera.
    if not x_active_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Como super admin debes enviar el header X-Active-Tenant con el "
                "UUID de la empresa sobre la que vas a operar."
            ),
        )
    try:
        org_uuid = UUID(x_active_tenant)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Active-Tenant inválido (no es un UUID).",
        )

    org = db.query(Organization).filter(Organization.id == org_uuid).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La empresa indicada en X-Active-Tenant no existe.",
        )
    if not org.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La empresa indicada está desactivada.",
        )
    return org.id


# ── Gating por plan (monetización) ───────────────────────────────────────────

def require_feature(feature: str):
    """
    Dependencia que exige que el plan de la organización habilite `feature`.

    Retorna la Organization (para que el handler pueda consumir créditos de IA).
    Responde 402 Payment Required si el plan no incluye la feature.
    """

    def guard(
        organization_id: UUID = Depends(get_active_organization_id),
        db: Session = Depends(get_db),
    ):
        from app.services import plan_service  # noqa: PLC0415

        org = plan_service.get_org(db, organization_id)
        if org is None or not plan_service.has_feature(org, feature):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Esta función no está incluida en tu plan. Mejora tu plan para usarla.",
            )
        return org

    return guard


# Atajos de uso frecuente
require_admin = require_role("admin")
require_editor_or_admin = require_role("admin", "editor")
require_any_role = get_current_user  # consultor, editor y admin
