"""Tests de alertas de vencimiento: listado, filtros y dismiss."""
import uuid
from datetime import datetime, date, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocStatus
from app.models.alert import DocumentAlert, AlertStatus, AlertType

ORG_ID = "00000000-0000-0000-0000-000000000001"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def alert_document(db: Session, admin_user) -> Document:
    db.query(Document).filter(
        Document.organization_id == ORG_ID,
        Document.original_filename == "doc_con_alerta.pdf",
    ).delete()
    db.commit()

    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename="doc_con_alerta.pdf",
        stored_path=f"{ORG_ID}/2026/06/{uuid.uuid4()}_alerta.pdf",
        file_type="pdf",
        file_size_kb=8,
        ocr_text="El contrato vence el 31 de diciembre de 2026.",
        status=DocStatus.classified,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    yield doc
    db.query(DocumentAlert).filter(DocumentAlert.document_id == doc.id).delete()
    db.query(Document).filter(Document.id == doc.id).delete()
    db.commit()


@pytest.fixture(scope="module")
def sample_alert(db: Session, alert_document: Document) -> DocumentAlert:
    alert = DocumentAlert(
        id=uuid.uuid4(),
        document_id=alert_document.id,
        organization_id=ORG_ID,
        alert_type=AlertType.expiry,
        detected_date=date.today(),
        alert_date=date.today() + timedelta(days=30),
        status=AlertStatus.pending,
        detail="El contrato vence el 31 de diciembre de 2026",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    yield alert
    db.query(DocumentAlert).filter(DocumentAlert.id == alert.id).delete()
    db.commit()


# ── Listado ───────────────────────────────────────────────────────────────────

def test_listar_alertas_admin(client: TestClient, admin_token: str, sample_alert):
    resp = client.get(
        "/api/v1/alerts/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_listar_alertas_editor(client: TestClient, editor_token: str, sample_alert):
    resp = client.get(
        "/api/v1/alerts/",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200


def test_listar_alertas_sin_token(client: TestClient):
    resp = client.get("/api/v1/alerts/")
    assert resp.status_code == 401


def test_listar_alertas_filtro_status_pending(
    client: TestClient, admin_token: str, sample_alert
):
    resp = client.get(
        "/api/v1/alerts/",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    for alert in resp.json():
        assert alert["status"] == "pending"


def test_listar_alertas_filtro_tipo_expiry(
    client: TestClient, admin_token: str, sample_alert
):
    resp = client.get(
        "/api/v1/alerts/",
        params={"alert_type": "expiry"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    for alert in resp.json():
        assert alert["alert_type"] == "expiry"


def test_listar_alertas_filtro_document_id(
    client: TestClient, admin_token: str, sample_alert, alert_document: Document
):
    resp = client.get(
        "/api/v1/alerts/",
        params={"document_id": str(alert_document.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    ids = [a["document_id"] for a in resp.json()]
    assert str(alert_document.id) in ids


def test_alerta_contiene_nombre_documento(
    client: TestClient, admin_token: str, sample_alert, alert_document: Document
):
    resp = client.get(
        "/api/v1/alerts/",
        params={"document_id": str(alert_document.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    alertas = resp.json()
    assert any(a["document_name"] == "doc_con_alerta.pdf" for a in alertas)


# ── Dismiss ───────────────────────────────────────────────────────────────────

def test_dismiss_alerta(
    client: TestClient, admin_token: str, db: Session, alert_document: Document
):
    """Marcar una alerta como dismissed actualiza el status."""
    alerta = DocumentAlert(
        id=uuid.uuid4(),
        document_id=alert_document.id,
        organization_id=ORG_ID,
        alert_type=AlertType.deadline,
        detected_date=date.today(),
        alert_date=date.today() + timedelta(days=7),
        status=AlertStatus.pending,
        detail="Fecha límite de entrega próxima",
    )
    db.add(alerta)
    db.commit()
    alert_id = str(alerta.id)

    resp = client.patch(
        f"/api/v1/alerts/{alert_id}/dismiss",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"

    db.delete(alerta)
    db.commit()


def test_dismiss_alerta_inexistente(client: TestClient, admin_token: str):
    resp = client.patch(
        f"/api/v1/alerts/{uuid.uuid4()}/dismiss",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_dismiss_alerta_sin_token(client: TestClient, sample_alert: DocumentAlert):
    resp = client.patch(f"/api/v1/alerts/{sample_alert.id}/dismiss")
    assert resp.status_code == 401
