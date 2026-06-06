"""Tests del chatbot (documental y global) — Gemini siempre mockeado."""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocStatus

ORG_ID = "00000000-0000-0000-0000-000000000001"
_GEMINI_REPLY = "Respuesta de prueba del asistente."


# ── Fixture: documento con texto OCR ─────────────────────────────────────────

@pytest.fixture(scope="module")
def chat_document(db: Session, admin_user) -> Document:
    db.query(Document).filter(
        Document.organization_id == ORG_ID,
        Document.original_filename == "chat_test_doc.pdf",
    ).delete()
    db.commit()

    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename="chat_test_doc.pdf",
        stored_path=f"{ORG_ID}/2026/06/{uuid.uuid4()}_chat.pdf",
        file_type="pdf",
        file_size_kb=12,
        ocr_text=(
            "Contrato de prestación de servicios firmado entre la UNAP "
            "y la empresa TechSoft S.A.C. con fecha 01 de junio de 2026. "
            "Monto: S/ 45,000.00. Vigencia: 6 meses."
        ),
        status=DocStatus.classified,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    yield doc
    db.query(Document).filter(Document.id == doc.id).delete()
    db.commit()


@pytest.fixture(scope="module")
def chat_document_sin_ocr(db: Session, admin_user) -> Document:
    db.query(Document).filter(
        Document.organization_id == ORG_ID,
        Document.original_filename == "sin_ocr_chat.pdf",
    ).delete()
    db.commit()

    doc = Document(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        uploaded_by=admin_user.id,
        original_filename="sin_ocr_chat.pdf",
        stored_path=f"{ORG_ID}/2026/06/{uuid.uuid4()}_sin_ocr.pdf",
        file_type="pdf",
        file_size_kb=5,
        ocr_text=None,
        status=DocStatus.pending,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    yield doc
    db.query(Document).filter(Document.id == doc.id).delete()
    db.commit()


# ── Chatbot documental ────────────────────────────────────────────────────────

def test_chat_documental_responde(
    client: TestClient, admin_token: str, chat_document: Document
):
    """El chatbot responde con reply y devuelve historial actualizado."""
    with patch("app.api.chat.gemini_service.chat", return_value=_GEMINI_REPLY):
        resp = client.post(
            f"/api/v1/chat/{chat_document.id}",
            json={"message": "¿Cuál es el monto del contrato?", "history": []},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "reply" in body
    assert body["reply"] == _GEMINI_REPLY
    assert len(body["history"]) == 2
    assert body["history"][-2]["role"] == "user"
    assert body["history"][-1]["role"] == "assistant"


def test_chat_documental_con_historial(
    client: TestClient, admin_token: str, chat_document: Document
):
    """El historial previo se concatena al nuevo turno."""
    history = [
        {"role": "user", "content": "¿Quién firmó?"},
        {"role": "assistant", "content": "La UNAP y TechSoft S.A.C."},
    ]
    with patch("app.api.chat.gemini_service.chat", return_value="Respuesta turno 2"):
        resp = client.post(
            f"/api/v1/chat/{chat_document.id}",
            json={"message": "¿Cuánto tiempo dura?", "history": history},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["history"]) == 4  # 2 previos + user + assistant


def test_chat_documental_sin_ocr(
    client: TestClient, admin_token: str, chat_document_sin_ocr: Document
):
    """Si el documento no tiene OCR, devuelve mensaje de aviso sin llamar a Gemini."""
    with patch("app.api.chat.gemini_service.chat") as mock_chat:
        resp = client.post(
            f"/api/v1/chat/{chat_document_sin_ocr.id}",
            json={"message": "¿Qué dice?", "history": []},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        mock_chat.assert_not_called()

    assert resp.status_code == 200
    assert "procesado" in resp.json()["reply"].lower()


def test_chat_documental_mensaje_vacio(
    client: TestClient, admin_token: str, chat_document: Document
):
    """Mensaje vacío retorna 400."""
    resp = client.post(
        f"/api/v1/chat/{chat_document.id}",
        json={"message": "   ", "history": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


def test_chat_documental_documento_inexistente(client: TestClient, admin_token: str):
    resp = client.post(
        f"/api/v1/chat/{uuid.uuid4()}",
        json={"message": "¿Qué dice?", "history": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_chat_documental_sin_token(client: TestClient, chat_document: Document):
    resp = client.post(
        f"/api/v1/chat/{chat_document.id}",
        json={"message": "pregunta", "history": []},
    )
    assert resp.status_code == 401


# ── Chatbot global ────────────────────────────────────────────────────────────

def test_chat_global_responde(client: TestClient, admin_token: str):
    """El chatbot global responde con estadísticas del sistema."""
    with patch("app.api.chat.gemini_service.chat_global", return_value="Tienes 5 documentos."):
        resp = client.post(
            "/api/v1/chat/global",
            json={"message": "¿Cuántos documentos hay?", "history": []},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "reply" in body
    assert body["reply"] == "Tienes 5 documentos."


def test_chat_global_mensaje_vacio(client: TestClient, admin_token: str):
    resp = client.post(
        "/api/v1/chat/global",
        json={"message": "", "history": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


def test_chat_global_sin_token(client: TestClient):
    resp = client.post(
        "/api/v1/chat/global",
        json={"message": "hola", "history": []},
    )
    assert resp.status_code == 401


def test_chat_global_editor(client: TestClient, editor_token: str):
    """Editor también puede usar el chatbot global."""
    with patch("app.api.chat.gemini_service.chat_global", return_value="Ok."):
        resp = client.post(
            "/api/v1/chat/global",
            json={"message": "¿Hay alertas?", "history": []},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
    assert resp.status_code == 200
