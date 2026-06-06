"""Servicio de digitalización: convierte texto OCR en un .docx descargable."""
import io
import logging
from datetime import datetime, timezone

logger = logging.getLogger("docmind")


def build_docx(ocr_text: str, source_filename: str) -> bytes:
    """
    Genera un documento .docx editable a partir del texto OCR.

    El archivo incluye un encabezado con el nombre del archivo original y la
    fecha de digitalización, seguido por el texto extraído párrafo por párrafo.
    Retorna los bytes del archivo (listos para subir a MinIO o servir).
    """
    from docx import Document  # noqa: PLC0415
    from docx.shared import Pt  # noqa: PLC0415

    doc = Document()

    # Estilo base
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # Encabezado
    title = doc.add_heading("Documento digitalizado", level=1)
    title.alignment = 0

    meta = doc.add_paragraph()
    meta.add_run(f"Archivo original: ").bold = True
    meta.add_run(source_filename)
    meta_date = doc.add_paragraph()
    meta_date.add_run("Digitalizado el: ").bold = True
    meta_date.add_run(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    doc.add_paragraph()  # espacio en blanco

    # Cuerpo: dividir por dobles saltos de línea como párrafos
    text = (ocr_text or "").strip()
    if not text:
        doc.add_paragraph(
            "[No se pudo extraer texto del documento original. "
            "Revise manualmente la imagen o el escaneo.]"
        )
    else:
        for block in text.split("\n\n"):
            block = block.strip()
            if block:
                doc.add_paragraph(block)

    buffer = io.BytesIO()
    doc.save(buffer)
    data = buffer.getvalue()
    buffer.close()

    logger.info(
        f"DOCX generado: {len(data)} bytes "
        f"({len(text)} chars de OCR, archivo origen={source_filename!r})"
    )
    return data
