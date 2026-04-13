"""
Crea un usuario administrador en la organización demo.

Uso:
    cd backend
    python scripts/create_admin.py admin@docmind.com password123

La organización demo tiene el ID fijo:
    00000000-0000-0000-0000-000000000001
"""
import sys
import os

# Añadir el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole

DEMO_ORG_ID = "00000000-0000-0000-0000-000000000001"


def create_admin(email: str, password: str, name: str = "Administrador") -> None:
    """Crea un usuario admin en la BD."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"[!] Ya existe un usuario con el email '{email}'")
            print(f"    ID: {existing.id} | Rol: {existing.role.value} | Activo: {existing.active}")
            return

        user = User(
            organization_id=DEMO_ORG_ID,
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.admin,
            active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"[OK] Administrador creado exitosamente")
        print(f"    ID:    {user.id}")
        print(f"    Email: {user.email}")
        print(f"    Org:   {user.organization_id}")
        print(f"    Rol:   {user.role.value}")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python scripts/create_admin.py <email> <password> [nombre]")
        print("Ejemplo: python scripts/create_admin.py admin@docmind.com MiPass123")
        sys.exit(1)

    email_arg = sys.argv[1]
    password_arg = sys.argv[2]
    name_arg = sys.argv[3] if len(sys.argv) > 3 else "Administrador"

    create_admin(email_arg, password_arg, name_arg)
