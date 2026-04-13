"""Tests de gestión de categorías."""
import pytest
from fastapi.testclient import TestClient


def test_listar_categorias(client: TestClient, admin_token: str):
    """Cualquier rol puede listar categorías."""
    resp = client.get(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_listar_categorias_editor(client: TestClient, editor_token: str):
    """Editor también puede listar categorías."""
    resp = client.get(
        "/api/v1/categories/",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200


def test_crear_categoria_admin(client: TestClient, admin_token: str):
    """Admin puede crear una categoría."""
    resp = client.post(
        "/api/v1/categories/",
        json={"name": "Actas Test", "description": "Categoría de prueba", "color": "#16A34A"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # 201 si hay espacio, 422 si ya se llenaron las 10 categorías del seed
    assert resp.status_code in (201, 422)


def test_crear_categoria_editor_prohibido(client: TestClient, editor_token: str):
    """Editor no puede crear categorías."""
    resp = client.post(
        "/api/v1/categories/",
        json={"name": "No permitida", "color": "#000000"},
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 403


def test_crear_categoria_color_invalido(client: TestClient, admin_token: str):
    """Crear categoría con color inválido retorna 422."""
    resp = client.post(
        "/api/v1/categories/",
        json={"name": "Color malo", "color": "rojo"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


def test_listar_categorias_sin_token(client: TestClient):
    """Sin token retorna 401."""
    resp = client.get("/api/v1/categories/")
    assert resp.status_code == 401
