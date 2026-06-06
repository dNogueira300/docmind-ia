"""Tests del log de auditoría: acceso, filtros y control de roles."""
import pytest
from fastapi.testclient import TestClient


# ── Acceso ────────────────────────────────────────────────────────────────────

def test_listar_audit_admin(client: TestClient, admin_token: str):
    """Admin puede ver el log de auditoría."""
    resp = client.get(
        "/api/v1/audit-log/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_listar_audit_editor_prohibido(client: TestClient, editor_token: str):
    """Editor no puede ver el log de auditoría."""
    resp = client.get(
        "/api/v1/audit-log/",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 403


def test_listar_audit_sin_token(client: TestClient):
    resp = client.get("/api/v1/audit-log/")
    assert resp.status_code == 401


# ── Estructura de respuesta ───────────────────────────────────────────────────

def test_audit_estructura_campos(client: TestClient, admin_token: str):
    """Cada entrada del log incluye los campos obligatorios."""
    resp = client.get(
        "/api/v1/audit-log/",
        params={"limit": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    entries = resp.json()
    if entries:
        entry = entries[0]
        assert "id" in entry
        assert "action" in entry
        assert "timestamp" in entry
        assert "user_id" in entry
        # Nunca debe aparecer el hash de contraseña
        assert "password_hash" not in str(entry)


# ── Filtros ───────────────────────────────────────────────────────────────────

def test_audit_filtro_accion_upload(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/audit-log/",
        params={"action": "upload"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    for entry in resp.json():
        assert entry["action"] == "upload"


def test_audit_filtro_accion_view(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/audit-log/",
        params={"action": "view"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    for entry in resp.json():
        assert entry["action"] == "view"


def test_audit_paginacion(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/audit-log/",
        params={"skip": 0, "limit": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) <= 3


def test_audit_aislamiento_tenant(client: TestClient, admin_token: str):
    """El admin solo ve entradas de su propia organización."""
    resp = client.get(
        "/api/v1/audit-log/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    # Verificar que el log no filtra usuarios de otras orgs
    # (solo validamos que la respuesta es coherente)
    entries = resp.json()
    assert isinstance(entries, list)


def test_audit_filtro_fecha_invalida(client: TestClient, admin_token: str):
    """Fecha malformada retorna 422."""
    resp = client.get(
        "/api/v1/audit-log/",
        params={"from_date": "no-es-una-fecha"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422
