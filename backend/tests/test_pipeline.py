"""Tests del pipeline OCR + NLP y endpoints de búsqueda y descarga."""
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocStatus
from app.models.category import Category


# ── Fixtures ──────────────────────────────────────────────────────────────────

ORG_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(scope="module")
def test_category(db: Session) -> Category:
    """Categoría de prueba para el pipeline."""
    existing = (
        db.query(Category)
        .filter(Category.organization_id == ORG_ID, Category.name == "Contratos Pipeline")
        .first()
    )
    if existing:
        return existing
    cat = Category(
        organization_id=ORG_ID,
        name="Contratos Pipeline",
        color="#2563D4",
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@pytest.fixture(scope="module")
def classified_document(db: Session, admin_user) -> Document:
    """
    Documento ya procesado (classified) con ocr_text para probar búsqueda full-text.
    Se inserta directamente en BD sin pasar por el pipeline.
    """
    # Limpiar si ya existe de una ejecución anterior
    db.query(Document).filter(
        Document.organization_id == ORG_ID,
        Document.original_filename == "contrato_pipeline_test.pdf",
    ).delete()
    db.commit()

    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename="contrato_pipeline_test.pdf",
        stored_path=f"{ORG_ID}/2026/04/{uuid.uuid4()}_contrato_pipeline_test.pdf",
        file_type="pdf",
        file_size_kb=10,
        ocr_text="Este contrato de servicios establece los términos y condiciones "
                 "para la prestación de servicios profesionales entre las partes.",
        ai_confidence_score=0.85,
        status=DocStatus.classified,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ── Tests del pipeline ────────────────────────────────────────────────────────

def test_pipeline_classified(db: Session, admin_user, test_category: Category):
    """
    Verifica que el pipeline actualiza el documento:
    pending → processing → classified cuando OCR y NLP tienen éxito.
    """
    from app.services.pipeline_service import process_document

    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename="test_classified.pdf",
        stored_path=f"{ORG_ID}/2026/04/test_classified.pdf",
        file_type="pdf",
        file_size_kb=5,
        status=DocStatus.pending,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)

    with patch("app.services.pipeline_service.ocr_service.extract_text") as mock_ocr, \
         patch("app.services.pipeline_service.nlp_service.classify_document") as mock_nlp:

        mock_ocr.return_value = "Contrato de servicios profesionales entre las partes."
        mock_nlp.return_value = (test_category.name, 0.92)

        process_document(doc_id, db)

    db.refresh(doc)
    assert doc.status == DocStatus.classified
    assert doc.ocr_text is not None
    assert doc.category_id == test_category.id
    assert doc.ai_confidence_score == pytest.approx(0.92)

    # Limpieza
    db.delete(doc)
    db.commit()


def test_pipeline_review_bajo_score(db: Session, admin_user, test_category: Category):
    """
    Verifica que score < 0.70 deja el documento en status='review'.
    """
    from app.services.pipeline_service import process_document

    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename="test_review.pdf",
        stored_path=f"{ORG_ID}/2026/04/test_review.pdf",
        file_type="pdf",
        file_size_kb=5,
        status=DocStatus.pending,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)

    with patch("app.services.pipeline_service.ocr_service.extract_text") as mock_ocr, \
         patch("app.services.pipeline_service.nlp_service.classify_document") as mock_nlp:

        mock_ocr.return_value = "Texto poco claro para clasificar."
        mock_nlp.return_value = (test_category.name, 0.45)

        process_document(doc_id, db)

    db.refresh(doc)
    assert doc.status == DocStatus.review
    assert doc.ai_confidence_score == pytest.approx(0.45)

    db.delete(doc)
    db.commit()


def test_pipeline_error_ocr(db: Session, admin_user):
    """
    Verifica que si OCR lanza una excepción, el documento queda en status='error'.
    """
    from app.services.pipeline_service import process_document

    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename="test_error.pdf",
        stored_path=f"{ORG_ID}/2026/04/test_error.pdf",
        file_type="pdf",
        file_size_kb=5,
        status=DocStatus.pending,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)

    with patch("app.services.pipeline_service.ocr_service.extract_text") as mock_ocr:
        mock_ocr.side_effect = RuntimeError("MinIO no disponible")
        process_document(doc_id, db)

    db.refresh(doc)
    assert doc.status == DocStatus.error

    db.delete(doc)
    db.commit()


# ── Tests de búsqueda full-text ───────────────────────────────────────────────

def test_busqueda_semantica(
    client: TestClient,
    admin_token: str,
    classified_document: Document,
):
    """Buscar por palabra clave que existe en ocr_text retorna el documento."""
    resp = client.get(
        "/api/v1/documents/search",
        params={"q": "contrato"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    ids = [r["id"] for r in results]
    assert str(classified_document.id) in ids


def test_busqueda_sin_query(client: TestClient, admin_token: str):
    """Búsqueda con q vacío retorna lista vacía."""
    resp = client.get(
        "/api/v1/documents/search",
        params={"q": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_busqueda_sin_token(client: TestClient):
    """Búsqueda sin token retorna 401."""
    resp = client.get("/api/v1/documents/search", params={"q": "contrato"})
    assert resp.status_code == 401


# ── Test de URL de descarga ───────────────────────────────────────────────────

def test_download_url(
    client: TestClient,
    admin_token: str,
    classified_document: Document,
):
    """El endpoint download-url retorna una URL firmada y expires_in_seconds."""
    with patch("app.services.minio_service.get_presigned_url") as mock_url:
        mock_url.return_value = "http://minio:9000/docmind-docs/signed-url-test"
        resp = client.get(
            f"/api/v1/documents/{classified_document.id}/download-url",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "download_url" in body
    assert "expires_in_seconds" in body
    assert body["expires_in_seconds"] == 3600
