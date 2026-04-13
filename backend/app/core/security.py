"""Utilidades de seguridad: hashing de contraseñas y manejo de JWT."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hashea una contraseña con bcrypt (12 rondas)."""
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con el hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(
    user_id: UUID,
    organization_id: UUID,
    role: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Crea un JWT con los datos del usuario. Expira en 8 horas por defecto."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "role": role,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    """Decodifica y valida un JWT. Lanza JWTError si es inválido o expirado."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
