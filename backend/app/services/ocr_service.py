"""Servicio OCR: extrae texto de PDFs e imágenes usando pytesseract y pypdf."""
import io
import logging

import pytesseract
from PIL import Image

from app.services import minio_service

logger = logging.getLogger("docmind")

# Límite de caracteres que se almacena en BD (campo ocr_text)
MAX_OCR_CHARS = 10_000

# Mínimo de caracteres para considerar que un PDF tiene texto digital
MIN_DIGITAL_TEXT_LENGTH = 50


def extract_text(stored_path: str, file_type: str) -> str:
    """
    Descarga el archivo desde MinIO y extrae su texto.

    Estrategia:
    - PDF con texto digital: pypdf (rápido, preciso)
    - PDF escaneado / JPG / PNG: Tesseract OCR con lang='spa'

    Retorna string vacío si ocurre cualquier error.
    """
    try:
        file_bytes = minio_service.get_file_bytes(stored_path)

        if file_type == "pdf":
            text = _extract_pdf(file_bytes)
        else:
            text = _extract_image(file_bytes)

        text = text.strip()
        logger.info(
            f"OCR completado: {len(text)} caracteres extraídos "
            f"(archivo={stored_path!r}, tipo={file_type})"
        )
        return text[:MAX_OCR_CHARS]

    except Exception as exc:
        logger.error(f"Error en OCR para '{stored_path}': {exc}")
        return ""


def _extract_pdf(file_bytes: bytes) -> str:
    """
    Intenta extraer texto de un PDF.
    1. pypdf para PDFs con texto digital.
    2. Tesseract como fallback para PDFs escaneados (primera página como imagen).
    """
    # Intentar extracción directa con pypdf
    try:
        import pypdf  # noqa: PLC0415

        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        text = " ".join(pages_text).strip()

        if len(text) >= MIN_DIGITAL_TEXT_LENGTH:
            logger.info("PDF con texto digital detectado — usando pypdf")
            return text

        logger.info("PDF con poco texto extraído por pypdf — intentando Tesseract")
    except Exception as exc:
        logger.warning(f"pypdf no pudo leer el PDF: {exc}")

    # Fallback: intentar abrir el PDF como imagen con Pillow
    return _pdf_as_image_ocr(file_bytes)


def _pdf_as_image_ocr(file_bytes: bytes) -> str:
    """
    Intenta abrir el PDF directamente con Pillow y aplicar Tesseract.
    Funciona para PDFs de una sola página que Pillow puede leer.
    Retorna string vacío si no es posible.
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(img, lang="spa")
        logger.info("PDF escaneado procesado con Tesseract via Pillow")
        return text
    except Exception as exc:
        logger.warning(f"No se pudo aplicar OCR al PDF escaneado: {exc}")
        return ""


def _extract_image(file_bytes: bytes) -> str:
    """Extrae texto de una imagen JPG o PNG con Tesseract (lang=spa)."""
    img = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(img, lang="spa")
    return text
