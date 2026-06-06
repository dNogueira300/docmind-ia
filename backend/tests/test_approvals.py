"""Tests del flujo de aprobaciones documentales: listado, aprobar, rechazar."""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocStatus
from app.models.approval import DocumentApproval, ApprovalStatus

ORG_ID = "00000000-0000-0000-0000-000000000001"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def approval_doc(db: Session, admin_user) -> Document:
    """Documento en pending_approval para cada test (scope=function para aislamiento)."""
    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename=f"aprobacion_{uuid.uuid4().hex[:6]}.pdf",
        stored_path=f"{ORG_ID}/2026/06/{uuid.uuid4()}_aprobacion.pdf",
        file_type="pdf",
        file_size_kb=10,
        status=DocStatus.pending_approval,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    yield doc
    db.query(DocumentApproval).filter(DocumentApproval.document_id == doc.id).delete()
    db.query(Document).filter(Document.id == doc.id).delete()
    db.commit()


@pytest.fixture
def pending_approval(db: Session, approval_doc: Document, admin_user) -> DocumentApproval:
    approval = DocumentApproval(
        document_id=approval_doc.id,
        organization_id=ORG_ID,
        requested_by=admin_user.id,
        status=ApprovalStatus.pending,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    yield approval


# ── Listado de aprobaciones ───────────────────────────────────────────────────

def test_listar_aprobaciones_admin(client: TestClient, admin_token: str, pending_approval):
    resp = client.get(
        "/api/v1/approvals/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_listar_aprobaciones_editor(client: TestClient, editor_token: str, pending_approval):
    resp = client.get(
        "/api/v1/approvals/",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200


def test_listar_aprobaciones_sin_token(client: TestClient):
    resp = client.get("/api/v1/approvals/")
    assert resp.status_code == 401


def test_listar_aprobaciones_filtro_pending(client: TestClient, admin_token: str, pending_approval):
    resp = client.get(
        "/api/v1/approvals/",
        params={"status": "pending"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    for item in resp.json():
        assert item["status"] == "pending"


# ── Aprobar ───────────────────────────────────────────────────────────────────

def test_aprobar_documento(
    client: TestClient, admin_token: str, approval_doc: Document, pending_approval, db: Session
):
    resp = client.post(
        f"/api/v1/approvals/{approval_doc.id}/approve",
        json={"comment": "Documento conforme al reglamento vigente."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["comment"] == "Documento conforme al reglamento vigente."

    # El documento debe quedar como classified
    db.refresh(approval_doc)
    assert approval_doc.status == DocStatus.classified


def test_aprobar_sin_aprobacion_pendiente(client: TestClient, admin_token: str):
    """Aprobar un doc sin solicitud pendiente retorna 404."""
    resp = client.post(
        f"/api/v1/approvals/{uuid.uuid4()}/approve",
        json={"comment": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ── Rechazar ─────────────────────────────────────────────────────────────────

def test_rechazar_documento(
    client: TestClient, admin_token: str, approval_doc: Document, pending_approval, db: Session
):
    resp = client.post(
        f"/api/v1/approvals/{approval_doc.id}/reject",
        json={"comment": "Falta la firma del responsable."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected"

    # El documento debe quedar en review para corrección manual
    db.refresh(approval_doc)
    assert approval_doc.status == DocStatus.review


def test_rechazar_sin_aprobacion_pendiente(client: TestClient, admin_token: str):
    resp = client.post(
        f"/api/v1/approvals/{uuid.uuid4()}/reject",
        json={"comment": "Sin motivo"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_aprobar_sin_token(client: TestClient, approval_doc: Document):
    resp = client.post(
        f"/api/v1/approvals/{approval_doc.id}/approve",
        json={"comment": ""},
    )
    assert resp.status_code == 401
