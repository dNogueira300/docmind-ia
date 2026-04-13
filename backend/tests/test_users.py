"""Tests de gestión de usuarios."""
import pytest
from fastapi.testclient import TestClient


def test_listar_usuarios_admin(client: TestClient, admin_token: str):
    """Admin puede listar usuarios de su organización."""
    resp = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_listar_usuarios_editor_prohibido(client: TestClient, editor_token: str):
    """Editor no puede listar usuarios — solo admin."""
    resp = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 403


def test_crear_usuario(client: TestClient, admin_token: str):
    """Admin puede crear un nuevo usuario."""
    resp = client.post(
        "/api/v1/users/",
        json={
            "name": "Consultor Test",
            "email": "consultor_test_001@docmind.com",
            "password": "pass1234",
            "role": "consultor",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "consultor_test_001@docmind.com"
    assert "password_hash" not in body  # nunca exponer el hash


def test_crear_usuario_email_duplicado(client: TestClient, admin_token: str):
    """Crear usuario con email ya existente retorna 409."""
    resp = client.post(
        "/api/v1/users/",
        json={
            "name": "Duplicado",
            "email": "consultor_test_001@docmind.com",
            "password": "pass1234",
            "role": "consultor",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


def test_crear_usuario_editor_prohibido(client: TestClient, editor_token: str):
    """Editor no puede crear usuarios."""
    resp = client.post(
        "/api/v1/users/",
        json={
            "name": "No permitido",
            "email": "nodeberia@docmind.com",
            "password": "pass1234",
            "role": "consultor",
        },
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 403
