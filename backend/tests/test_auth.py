"""Tests de autenticación."""
import pytest
from fastapi.testclient import TestClient


def test_login_exitoso(client: TestClient, admin_user):
    """Login con credenciales correctas retorna un JWT."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.email, "password": "admin1234"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_password_incorrecta(client: TestClient, admin_user):
    """Login con contraseña incorrecta retorna 401."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.email, "password": "contraseña_incorrecta"},
    )
    assert resp.status_code == 401


def test_login_email_inexistente(client: TestClient):
    """Login con email que no existe retorna 401."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "noexiste@docmind.com", "password": "cualquiera"},
    )
    assert resp.status_code == 401


def test_acceso_sin_token(client: TestClient):
    """Endpoint protegido sin token retorna 401."""
    resp = client.get("/api/v1/users/")
    assert resp.status_code == 401


def test_logout(client: TestClient, admin_token: str):
    """Logout con token válido retorna 200."""
    resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200


def test_health_check(client: TestClient):
    """El health check es público y retorna ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
