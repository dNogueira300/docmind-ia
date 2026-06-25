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


def test_aprobar_sugerencia_clasifica_en_lote(client: TestClient, admin_token: str, db, admin_user):
    """
    Al aprobar una sugerencia, TODOS los documentos en review marcados por la IA
    con esa categoría (ai_suggested_category) se clasifican en lote, sin re-llamar
    a Gemini.
    """
    import uuid
    from datetime import datetime, timezone
    from app.models.document import Document, DocStatus
    from app.models.category import Category
    from app.models.category_suggestion import CategorySuggestion

    ORG_ID = "00000000-0000-0000-0000-000000000001"
    NAME = "Cartas Bulk Test"

    # Limpieza de restos de ejecuciones anteriores
    db.query(CategorySuggestion).filter(
        CategorySuggestion.organization_id == ORG_ID,
        CategorySuggestion.suggested_name == NAME,
    ).delete()
    db.query(Category).filter(
        Category.organization_id == ORG_ID, Category.name == NAME
    ).delete()
    db.query(Document).filter(
        Document.organization_id == ORG_ID,
        Document.ai_suggested_category == NAME,
    ).delete()
    db.commit()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    docs = []
    for i in range(2):
        d = Document(
            id=uuid.uuid4(),
            organization_id=ORG_ID,
            uploaded_by=admin_user.id,
            original_filename=f"bulk_{i}.pdf",
            stored_path=f"{ORG_ID}/2026/06/bulk_{i}.pdf",
            file_type="pdf",
            file_size_kb=5,
            status=DocStatus.review,
            category_id=None,
            ai_suggested_category=NAME,
            created_at=now,
            updated_at=now,
        )
        db.add(d)
        docs.append(d)
    db.flush()  # insertar los documentos antes de la sugerencia (FK document_id)
    suggestion = CategorySuggestion(
        organization_id=ORG_ID,
        document_id=docs[0].id,
        suggested_name=NAME,
        confidence=0.9,
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)

    resp = client.post(
        f"/api/v1/categories/suggestions/{suggestion.id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    cat = resp.json()
    assert cat["name"] == NAME

    # Los DOS documentos quedaron clasificados con la nueva categoría
    for d in docs:
        db.refresh(d)
        assert d.status == DocStatus.classified
        assert str(d.category_id) == cat["id"]

    # Limpieza
    for d in docs:
        db.delete(d)
    db.query(Category).filter(Category.id == cat["id"]).delete()
    db.commit()
