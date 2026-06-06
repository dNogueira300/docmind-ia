"""Tests de documentos: listado, filtros, detalle, reclasificación, eliminación, stats."""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocStatus
from app.models.category import Category

ORG_ID = "00000000-0000-0000-0000-000000000001"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def doc_category(db: Session) -> Category:
    existing = (
        db.query(Category)
        .filter(Category.organization_id == ORG_ID, Category.name == "Resoluciones Test")
        .first()
    )
    if existing:
        return existing
    cat = Category(organization_id=ORG_ID, name="Resoluciones Test", color="#7C3AED")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@pytest.fixture(scope="module")
def sample_doc(db: Session, admin_user, doc_category: Category):
    db.query(Document).filter(
        Document.organization_id == ORG_ID,
        Document.original_filename == "doc_test_suite.pdf",
    ).delete()
    db.commit()

    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename="doc_test_suite.pdf",
        stored_path=f"{ORG_ID}/2026/06/{uuid.uuid4()}_doc_test_suite.pdf",
        file_type="pdf",
        file_size_kb=20,
        ocr_text="Resolución rectoral N.° 047-2026 aprobando el presupuesto institucional.",
        ai_confidence_score=0.91,
        status=DocStatus.classified,
        category_id=doc_category.id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    yield doc
    db.query(Document).filter(Document.id == doc.id).delete()
    db.commit()


# ── Listado ───────────────────────────────────────────────────────────────────

def test_listar_documentos_admin(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_listar_documentos_editor(client: TestClient, editor_token: str):
    resp = client.get(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_listar_documentos_sin_token(client: TestClient):
    resp = client.get("/api/v1/documents/")
    assert resp.status_code == 401


def test_listar_filtro_status_classified(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/documents/",
        params={"status": "classified"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    for doc in resp.json():
        assert doc["status"] == "classified"


def test_listar_filtro_file_type_pdf(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/documents/",
        params={"file_type": "pdf"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    for doc in resp.json():
        assert doc["file_type"] == "pdf"


def test_listar_paginacion(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/documents/",
        params={"skip": 0, "limit": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) <= 2


# ── Detalle ───────────────────────────────────────────────────────────────────

def test_detalle_documento(client: TestClient, admin_token: str, sample_doc: Document):
    resp = client.get(
        f"/api/v1/documents/{sample_doc.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(sample_doc.id)
    assert body["original_filename"] == "doc_test_suite.pdf"
    assert body["status"] == "classified"
    assert "ocr_text" in body


def test_detalle_documento_editor(client: TestClient, editor_token: str, sample_doc: Document):
    resp = client.get(
        f"/api/v1/documents/{sample_doc.id}",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200


def test_detalle_documento_inexistente(client: TestClient, admin_token: str):
    resp = client.get(
        f"/api/v1/documents/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_detalle_sin_token(client: TestClient, sample_doc: Document):
    resp = client.get(f"/api/v1/documents/{sample_doc.id}")
    assert resp.status_code == 401


# ── Reclasificación ───────────────────────────────────────────────────────────

def test_reclasificar_admin(
    client: TestClient, admin_token: str, sample_doc: Document, doc_category: Category
):
    resp = client.put(
        f"/api/v1/documents/{sample_doc.id}/category",
        json={"category_id": str(doc_category.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "classified"
    assert resp.json()["category_id"] == str(doc_category.id)


def test_reclasificar_editor(
    client: TestClient, editor_token: str, sample_doc: Document, doc_category: Category
):
    resp = client.put(
        f"/api/v1/documents/{sample_doc.id}/category",
        json={"category_id": str(doc_category.id)},
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200


def test_reclasificar_categoria_otra_org(
    client: TestClient, admin_token: str, sample_doc: Document
):
    """Una categoría de otra organización retorna 404."""
    resp = client.put(
        f"/api/v1/documents/{sample_doc.id}/category",
        json={"category_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_reclasificar_documento_inexistente(
    client: TestClient, admin_token: str, doc_category: Category
):
    resp = client.put(
        f"/api/v1/documents/{uuid.uuid4()}/category",
        json={"category_id": str(doc_category.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ── Preview y descarga ────────────────────────────────────────────────────────

def test_preview_url(client: TestClient, admin_token: str, sample_doc: Document):
    with patch("app.services.minio_service.get_presigned_url") as mock_url:
        mock_url.return_value = "http://minio/presigned-preview"
        resp = client.get(
            f"/api/v1/documents/{sample_doc.id}/preview-url",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "preview_url" in body
    assert body["file_type"] == "pdf"
    assert body["expires_in_seconds"] == 3600


def test_digitalized_url_sin_docx(
    client: TestClient, admin_token: str, sample_doc: Document
):
    """Documento sin digitalized_path devuelve 404."""
    resp = client.get(
        f"/api/v1/documents/{sample_doc.id}/digitalized-url",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_digitalized_url_con_docx(
    client: TestClient, admin_token: str, db: Session, admin_user, doc_category: Category
):
    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename="digitalizado.pdf",
        stored_path=f"{ORG_ID}/2026/06/{uuid.uuid4()}_digitalizado.pdf",
        digitalized_path=f"{ORG_ID}/2026/06/digitalizado.docx",
        file_type="pdf",
        file_size_kb=5,
        status=DocStatus.classified,
        category_id=doc_category.id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(doc)
    db.commit()

    with patch("app.services.minio_service.get_presigned_url") as mock_url:
        mock_url.return_value = "http://minio/presigned-docx"
        resp = client.get(
            f"/api/v1/documents/{doc.id}/digitalized-url",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    assert "download_url" in resp.json()

    db.delete(doc)
    db.commit()


# ── Eliminación ───────────────────────────────────────────────────────────────

def test_eliminar_documento_admin(
    client: TestClient, admin_token: str, db: Session, admin_user
):
    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename="a_eliminar.pdf",
        stored_path=f"{ORG_ID}/2026/06/{uuid.uuid4()}_a_eliminar.pdf",
        file_type="pdf",
        file_size_kb=5,
        status=DocStatus.classified,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)

    with patch("app.services.minio_service.delete_file"):
        resp = client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    assert "eliminado" in resp.json()["detail"].lower()


def test_eliminar_documento_editor_prohibido(
    client: TestClient, editor_token: str, sample_doc: Document
):
    resp = client.delete(
        f"/api/v1/documents/{sample_doc.id}",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 403


def test_eliminar_documento_inexistente(client: TestClient, admin_token: str):
    with patch("app.services.minio_service.delete_file"):
        resp = client.delete(
            f"/api/v1/documents/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 404


# ── Estadísticas ──────────────────────────────────────────────────────────────

def test_stats_por_categoria(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/documents/stats/by-category",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    if items:
        assert "category_id" in items[0]
        assert "count" in items[0]


def test_stats_por_usuario(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/documents/stats/by-user",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    if items:
        assert "user_name" in items[0]
        assert "count" in items[0]


def test_stats_por_riesgo(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/documents/stats/by-risk",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_stats_sin_token(client: TestClient):
    resp = client.get("/api/v1/documents/stats/by-category")
    assert resp.status_code == 401
