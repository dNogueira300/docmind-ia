"""Fixtures compartidos para todos los tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.models.base import Base
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.category import Category

# ── Base de datos de prueba ───────────────────────────────────────────────────
# Usa la misma BD Docker pero en un schema de prueba (o simplemente la misma BD)
TEST_DB_URL = settings.db_url

test_engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

ORG_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(scope="session")
def db() -> Session:
    """Sesión de BD reutilizada para toda la sesión de tests."""
    session = TestSessionLocal()
    # Limpiar datos de tests anteriores para garantizar idempotencia
    session.query(User).filter(User.email == "consultor_test_001@docmind.com").delete()
    session.query(Category).filter(
        Category.organization_id == ORG_ID,
        Category.name == "Actas Test",
    ).delete()
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def admin_user(db: Session) -> User:
    """Crea o retorna el usuario admin de prueba."""
    existing = (
        db.query(User)
        .filter(User.email == "admin@test.docmind")
        .first()
    )
    if existing:
        return existing

    user = User(
        organization_id=ORG_ID,
        name="Admin Test",
        email="admin@test.docmind",
        password_hash=hash_password("admin1234"),
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="session")
def editor_user(db: Session) -> User:
    """Crea o retorna el usuario editor de prueba."""
    existing = (
        db.query(User)
        .filter(User.email == "editor@test.docmind")
        .first()
    )
    if existing:
        return existing

    user = User(
        organization_id=ORG_ID,
        name="Editor Test",
        email="editor@test.docmind",
        password_hash=hash_password("editor1234"),
        role=UserRole.editor,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="session")
def client(db: Session, admin_user: User, editor_user: User) -> TestClient:
    """Cliente HTTP de prueba con la BD de Docker."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client: TestClient, admin_user: User) -> str:
    """Obtiene un token JWT para el admin."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.email, "password": "admin1234"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def editor_token(client: TestClient, editor_user: User) -> str:
    """Obtiene un token JWT para el editor."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": editor_user.email, "password": "editor1234"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
