"""
Tests de seguridad en subida de archivos.

Cubre la validación por magic bytes, tamaño máximo, Content-Type declarado
y archivo vacío según CLAUDE.md § File upload security.
"""
import io
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Magic bytes reales para los tipos permitidos
PDF_MAGIC = b"%PDF-1.4 minimal\n"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
JPG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 20


def _upload(client, token, content: bytes, filename: str, content_type: str):
    """Helper: POST /upload con archivo en memoria."""
    return client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


# ── Happy paths ───────────────────────────────────────────────────────────────

def test_upload_pdf_exitoso(client: TestClient, editor_token: str):
    """PDF válido con magic bytes correctos y mock de MinIO retorna 201."""
    fake_path = "00000000-0000-0000-0000-000000000001/2026/06/test.pdf"
    with patch("app.api.documents.minio_service.upload_file", return_value=fake_path), \
         patch("app.api.documents.process_document"):
        resp = _upload(client, editor_token, PDF_MAGIC, "factura.pdf", "application/pdf")
    assert resp.status_code == 201
    body = resp.json()
    assert body["original_filename"] == "factura.pdf"
    assert body["status"] == "pending"


def test_upload_png_exitoso(client: TestClient, editor_token: str):
    """PNG válido retorna 201."""
    fake_path = "00000000-0000-0000-0000-000000000001/2026/06/test.png"
    with patch("app.api.documents.minio_service.upload_file", return_value=fake_path), \
         patch("app.api.documents.process_document"):
        resp = _upload(client, editor_token, PNG_MAGIC, "imagen.png", "image/png")
    assert resp.status_code == 201


def test_upload_jpg_exitoso(client: TestClient, editor_token: str):
    """JPG válido retorna 201."""
    fake_path = "00000000-0000-0000-0000-000000000001/2026/06/test.jpg"
    with patch("app.api.documents.minio_service.upload_file", return_value=fake_path), \
         patch("app.api.documents.process_document"):
        resp = _upload(client, editor_token, JPG_MAGIC, "foto.jpg", "image/jpeg")
    assert resp.status_code == 201


# ── Validación de Content-Type ────────────────────────────────────────────────

def test_upload_content_type_invalido(client: TestClient, editor_token: str):
    """Content-Type no permitido (text/plain) retorna 422 antes de leer el archivo."""
    resp = _upload(client, editor_token, PDF_MAGIC, "archivo.txt", "text/plain")
    assert resp.status_code == 422


def test_upload_content_type_zip(client: TestClient, editor_token: str):
    resp = _upload(client, editor_token, b"PK\x03\x04malware", "exploit.zip", "application/zip")
    assert resp.status_code == 422


# ── Validación por magic bytes ────────────────────────────────────────────────

def test_upload_magic_bytes_invalidos_con_content_type_pdf(client: TestClient, editor_token: str):
    """Content-Type=PDF pero magic bytes son de un ejecutable → 422."""
    exe_bytes = b"MZ\x90\x00" + b"\x00" * 20  # DOS/PE header
    resp = _upload(client, editor_token, exe_bytes, "malware.pdf", "application/pdf")
    assert resp.status_code == 422


def test_upload_png_con_content_type_pdf(client: TestClient, editor_token: str):
    """
    PNG con Content-Type=PDF: el sistema detecta el tipo real por magic bytes (\x89PNG)
    y sube el archivo como PNG (tipo válido). No lanza error porque ambos tipos son
    permitidos — el sistema confía en magic bytes, no en el Content-Type declarado.
    """
    fake_path = "00000000-0000-0000-0000-000000000001/2026/06/test_png_renamed.png"
    with patch("app.api.documents.minio_service.upload_file", return_value=fake_path), \
         patch("app.api.documents.process_document"):
        resp = _upload(client, editor_token, PNG_MAGIC, "trampa.pdf", "application/pdf")
    assert resp.status_code == 201
    assert resp.json()["file_type"] == "png"  # detectado por magic bytes, no por Content-Type


# ── Archivo vacío ─────────────────────────────────────────────────────────────

def test_upload_archivo_vacio(client: TestClient, editor_token: str):
    """Archivo de 0 bytes retorna 400."""
    resp = _upload(client, editor_token, b"", "vacio.pdf", "application/pdf")
    assert resp.status_code == 400


# ── Tamaño máximo (20 MB) ─────────────────────────────────────────────────────

def test_upload_archivo_demasiado_grande(client: TestClient, editor_token: str):
    """Archivo de 21 MB retorna 413."""
    big_file = PDF_MAGIC + b"\x00" * (21 * 1024 * 1024)
    resp = _upload(client, editor_token, big_file, "gigante.pdf", "application/pdf")
    assert resp.status_code == 413


# ── Control de acceso ─────────────────────────────────────────────────────────

def test_upload_sin_token(client: TestClient):
    """Sin token retorna 401."""
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", io.BytesIO(PDF_MAGIC), "application/pdf")},
    )
    assert resp.status_code == 401


def test_upload_consultor_prohibido(client: TestClient, db, admin_user):
    """Consultor no puede subir documentos."""
    from app.models.user import User, UserRole
    from app.models.audit_log import AuditLog
    from app.core.security import hash_password

    # Limpiar cualquier transacción fallida de un test previo
    db.rollback()

    def _delete_consultor():
        u = db.query(User).filter(User.email == "consultor_upload_test@docmind.com").first()
        if u:
            # audit_log.user_id es NOT NULL con RESTRICT — borrar primero las entradas
            db.query(AuditLog).filter(AuditLog.user_id == u.id).delete(synchronize_session=False)
            db.delete(u)
            db.commit()

    # Idempotencia: eliminar si ya existe de una ejecución anterior
    _delete_consultor()

    consultor = User(
        organization_id="00000000-0000-0000-0000-000000000001",
        name="Consultor Upload",
        email="consultor_upload_test@docmind.com",
        password_hash=hash_password("pass1234"),
        role=UserRole.consultor,
    )
    db.add(consultor)
    db.commit()

    resp_login = client.post(
        "/api/v1/auth/login",
        data={"username": "consultor_upload_test@docmind.com", "password": "pass1234", "org_slug": "demo"},
    )
    token = resp_login.json()["access_token"]

    resp = _upload(client, token, PDF_MAGIC, "doc.pdf", "application/pdf")
    assert resp.status_code == 403

    # Limpieza: primero audit_log (NOT NULL), luego el usuario
    _delete_consultor()


# ── Reprocesamiento ───────────────────────────────────────────────────────────

def test_reprocess_documento_review(client: TestClient, editor_token: str, db, admin_user):
    """Reprocesar un documento en estado 'review' devuelve 200 con status=pending."""
    from app.models.document import Document, DocStatus
    import uuid
    from datetime import datetime, timezone

    db.rollback()  # limpiar estado fallido de tests previos

    doc = Document(
        id=uuid.uuid4(),
        organization_id="00000000-0000-0000-0000-000000000001",
        uploaded_by=admin_user.id,
        original_filename="reprocess_test.pdf",
        stored_path=f"00000000-0000-0000-0000-000000000001/2026/06/{uuid.uuid4()}_reprocess.pdf",
        file_type="pdf",
        file_size_kb=5,
        status=DocStatus.review,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(doc)
    db.commit()

    with patch("app.api.documents.process_document"):
        resp = client.patch(
            f"/api/v1/documents/{doc.id}/reprocess",
            headers={"Authorization": f"Bearer {editor_token}"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

    db.delete(doc)
    db.commit()


def test_reprocess_documento_classified_falla(client: TestClient, editor_token: str, db, admin_user):
    """Reprocesar un documento ya clasificado retorna 400."""
    from app.models.document import Document, DocStatus
    import uuid
    from datetime import datetime, timezone

    db.rollback()  # limpiar estado fallido de tests previos

    doc = Document(
        id=uuid.uuid4(),
        organization_id="00000000-0000-0000-0000-000000000001",
        uploaded_by=admin_user.id,
        original_filename="classified_reprocess.pdf",
        stored_path=f"00000000-0000-0000-0000-000000000001/2026/06/{uuid.uuid4()}_class.pdf",
        file_type="pdf",
        file_size_kb=5,
        status=DocStatus.classified,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(doc)
    db.commit()

    resp = client.patch(
        f"/api/v1/documents/{doc.id}/reprocess",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 400

    db.delete(doc)
    db.commit()
