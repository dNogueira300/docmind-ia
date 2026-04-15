"""
Script de prueba manual del pipeline OCR + NLP.

Uso:
    cd backend
    python scripts/test_pipeline.py [ruta_al_pdf]

Ejemplo:
    python scripts/test_pipeline.py docs/contrato_ejemplo.pdf

Si no se pasa un archivo, el script crea un PDF de prueba en memoria.
"""
import sys
import os
import time
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@docmind.com"
ADMIN_PASSWORD = "admin1234"


def _crear_pdf_prueba() -> bytes:
    """Genera un PDF mínimo con texto en español para probar el pipeline."""
    try:
        import pypdf
        from pypdf import PdfWriter

        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        # pypdf no soporta agregar texto directamente; usamos un PDF con texto embebido
    except Exception:
        pass

    # PDF mínimo válido con texto embebido (generado manualmente)
    pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
  /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 120 >>
stream
BT
/F1 12 Tf
50 700 Td
(Contrato de servicios profesionales entre las partes.) Tj
0 -20 Td
(Este documento establece los terminos y condiciones.) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000446 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
525
%%EOF"""
    return pdf_content


def login(session: requests.Session) -> str:
    """Hace login y retorna el token JWT."""
    resp = session.post(
        f"{BASE_URL}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if resp.status_code != 200:
        print(f"[ERROR] Login fallido: {resp.status_code} {resp.text}")
        sys.exit(1)
    token = resp.json()["access_token"]
    print(f"[OK] Login exitoso como {ADMIN_EMAIL}")
    return token


def subir_documento(session: requests.Session, token: str, pdf_path: str) -> str:
    """Sube el PDF y retorna el ID del documento."""
    with open(pdf_path, "rb") as f:
        file_data = f.read()

    resp = session.post(
        f"{BASE_URL}/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (os.path.basename(pdf_path), file_data, "application/pdf")},
    )
    if resp.status_code != 201:
        print(f"[ERROR] Upload fallido: {resp.status_code} {resp.text}")
        sys.exit(1)

    doc = resp.json()
    doc_id = doc["id"]
    print(f"[OK] Documento subido: ID={doc_id} status={doc['status']}")
    return doc_id


def consultar_documento(session: requests.Session, token: str, doc_id: str) -> dict:
    """Consulta el estado actual del documento."""
    resp = session.get(
        f"{BASE_URL}/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code != 200:
        print(f"[ERROR] Consulta fallida: {resp.status_code} {resp.text}")
        return {}
    return resp.json()


def mostrar_resultado(doc: dict) -> None:
    """Imprime el resultado del pipeline."""
    print("\n" + "=" * 60)
    print("RESULTADO DEL PIPELINE")
    print("=" * 60)
    print(f"  ID:          {doc.get('id')}")
    print(f"  Archivo:     {doc.get('original_filename')}")
    print(f"  Status:      {doc.get('status')}")
    print(f"  Score IA:    {doc.get('ai_confidence_score')}")
    print(f"  Categoría:   {doc.get('category_id')}")

    ocr_text = doc.get("ocr_text") or ""
    preview = ocr_text[:200].replace("\n", " ")
    print(f"  OCR (200c):  {preview!r}" if preview else "  OCR:         (vacío)")
    print("=" * 60)


def main() -> None:
    # Determinar archivo de prueba
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        if not os.path.exists(pdf_path):
            print(f"[ERROR] Archivo no encontrado: {pdf_path}")
            sys.exit(1)
    else:
        # Crear PDF de prueba temporal
        pdf_path = "/tmp/docmind_test_pipeline.pdf"
        with open(pdf_path, "wb") as f:
            f.write(_crear_pdf_prueba())
        print(f"[INFO] PDF de prueba creado en {pdf_path}")

    session = requests.Session()

    # 1. Login
    token = login(session)

    # 2. Subir documento
    doc_id = subir_documento(session, token, pdf_path)

    # 3. Esperar y consultar periódicamente
    print("\n[INFO] Esperando que el pipeline procese el documento...")
    for intento in range(1, 7):
        time.sleep(5)
        doc = consultar_documento(session, token, doc_id)
        current_status = doc.get("status", "desconocido")
        print(f"  [{intento * 5}s] status={current_status}")
        if current_status in ("classified", "review", "error"):
            break

    # 4. Resultado final
    mostrar_resultado(doc)


if __name__ == "__main__":
    main()
