"""Servicio OCR: extrae texto de PDFs e imágenes usando pytesseract y pypdf."""
import io
import logging
from typing import Optional

import pytesseract
from PIL import Image

from app.services import minio_service

logger = logging.getLogger("docmind")

MAX_OCR_CHARS = 10_000
MIN_DIGITAL_TEXT_LENGTH = 50

# DPI para rasterizar al generar el PDF con capa OCR. Equilibrio entre apariencia
# y memoria (rasterizar alto en multipágina dispara la RAM en Railway).
SEARCHABLE_PDF_DPI = 150

# Secuencia de intentos: (usar_preprocesamiento, lang, psm)
_OCR_ATTEMPTS = [
    (True,  "spa",     3),
    (True,  "spa",     6),   # uniform block — mejor para cartas formales
    (False, "spa",     6),
    (False, "spa",     3),
    (False, "spa",     4),
    (False, "spa+eng", 6),
    (False, "spa+eng", 3),
    (False, "eng",     6),
    (False, "eng",     3),
]

# DPI a probar en orden. Reducido para producción (Railway): rasterizar a 300 DPI
# PDFs de varias páginas consume mucha memoria/CPU. Secuencia escalada ×0.5.
_DPI_SEQUENCE = [150, 100, 75]

# Por encima de este umbral consideramos el resultado "suficientemente bueno"
# y dejamos de probar combinaciones. 500 chars ≈ un párrafo completo.
_CHARS_GOOD_ENOUGH = 500


def extract_text(stored_path: str, file_type: str) -> str:
    try:
        file_bytes = minio_service.get_file_bytes(stored_path)
        text = (_extract_pdf(file_bytes) if file_type == "pdf"
                else _extract_image(file_bytes))
        text = text.strip()
        logger.info(
            f"OCR completado: {len(text)} chars (archivo={stored_path!r}, tipo={file_type})"
        )
        return text[:MAX_OCR_CHARS]
    except Exception as exc:
        logger.error(f"Error en OCR para '{stored_path}': {exc}")
        return ""


def build_searchable_pdf(stored_path: str, file_type: str) -> Optional[bytes]:
    """
    Genera un PDF con capa de texto OCR sobre el documento original.

    Mantiene la apariencia del original (la imagen) y añade una capa de texto
    invisible seleccionable/editable en cualquier editor de PDF. Aplica a PDFs
    escaneados e imágenes (jpg/png).

    Returns:
        Bytes del PDF, o None si no se pudo generar.
    """
    try:
        file_bytes = minio_service.get_file_bytes(stored_path)

        if file_type == "pdf":
            from pdf2image import convert_from_bytes  # noqa: PLC0415
            pages = convert_from_bytes(file_bytes, dpi=SEARCHABLE_PDF_DPI)
        else:
            pages = [Image.open(io.BytesIO(file_bytes))]

        page_pdfs: list[bytes] = []
        for img in pages:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            page_pdfs.append(
                pytesseract.image_to_pdf_or_hocr(img, lang="spa", extension="pdf")
            )

        if not page_pdfs:
            return None
        if len(page_pdfs) == 1:
            return page_pdfs[0]

        import pypdf  # noqa: PLC0415
        writer = pypdf.PdfWriter()
        for pb in page_pdfs:
            writer.append(pypdf.PdfReader(io.BytesIO(pb)))
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()

    except Exception as exc:
        logger.error(
            f"Error generando PDF con OCR para '{stored_path}': {exc}", exc_info=True
        )
        return None


def _extract_pdf(file_bytes: bytes) -> str:
    # 1. Intento digital con pypdf
    try:
        import pypdf  # noqa: PLC0415
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        text = " ".join(p.extract_text() or "" for p in reader.pages).strip()
        if len(text) >= MIN_DIGITAL_TEXT_LENGTH:
            logger.info("PDF digital detectado — usando pypdf")
            return text
        logger.info("Poco texto en pypdf — intentando Tesseract")
    except Exception as exc:
        logger.warning(f"pypdf falló: {exc}")

    return _pdf_as_image_ocr(file_bytes)


def _img_to_bytes(img: "Image.Image", fmt: str = "PNG") -> bytes:
    """Convierte una PIL Image a bytes para enviar a Gemini Vision."""
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _pdf_as_image_ocr(file_bytes: bytes) -> str:
    """
    Intenta extraer texto con diferentes DPI.
    Para cada DPI prueba TODAS las combinaciones PSM/lang y toma la mejor.
    Si Tesseract falla en todos los intentos, usa Gemini Vision como último recurso.
    """
    last_pages: list["Image.Image"] = []

    try:
        from pdf2image import convert_from_bytes  # noqa: PLC0415

        for dpi in _DPI_SEQUENCE:
            pages = convert_from_bytes(file_bytes, dpi=dpi)
            last_pages = pages
            logger.info(f"pdf2image: {len(pages)} página(s) a {dpi} DPI")

            text_parts = []
            total_chars = 0

            for i, page_img in enumerate(pages, start=1):
                page_text = _ocr_best_attempt(page_img, page_num=i, total=len(pages), dpi=dpi)
                text_parts.append(page_text)
                total_chars += len(page_text.strip())

            if total_chars >= 200:
                result = "\n\n".join(t.strip() for t in text_parts if t.strip())
                logger.info(f"DPI {dpi} → {total_chars} chars totales. Usando este resultado.")
                return result

            logger.info(
                f"DPI {dpi} → solo {total_chars} chars (umbral: 200). "
                "Probando DPI menor para mejor calidad de imagen."
            )

    except Exception as exc:
        logger.warning(f"pdf2image falló: {exc}")

    # ── Fallback: Gemini Vision ──────────────────────────────────────────────
    # Tesseract no pudo extraer texto en ningún DPI/PSM. Enviamos las imágenes
    # a Gemini (multimodal) que maneja documentos oscuros/borrosos mucho mejor.
    if last_pages:
        logger.info(
            f"Tesseract falló en todos los intentos. "
            f"Intentando con Gemini Vision ({len(last_pages)} página(s))…"
        )
        from app.services import gemini_service  # noqa: PLC0415

        gemini_parts: list[str] = []
        for i, page_img in enumerate(last_pages, start=1):
            img_bytes = _img_to_bytes(page_img, fmt="PNG")
            page_text = gemini_service.extract_text_from_image(img_bytes, mime_type="image/png")
            if page_text.strip():
                gemini_parts.append(page_text.strip())
                logger.info(f"Gemini Vision p{i}/{len(last_pages)} → {len(page_text)} chars")

        if gemini_parts:
            return "\n\n".join(gemini_parts)

    logger.warning("No se pudo extraer texto útil del PDF con Tesseract ni con Gemini Vision.")
    return ""


def _analyze_image(img: "Image.Image") -> dict:
    """
    Analiza brillo medio y desviación estándar de la imagen.
    Devuelve {'mean': float, 'std': float, 'likely_inverted': bool, 'likely_blank': bool}
    """
    from PIL import ImageStat  # noqa: PLC0415
    gray = img.convert("L")
    stat = ImageStat.Stat(gray)
    mean = stat.mean[0]
    std  = stat.stddev[0]
    return {
        "mean": mean,
        "std":  std,
        "likely_inverted": mean < 50 and std > 10,   # fondo oscuro con algo de variación
        "likely_blank":    std < 5,                   # sin variación = página en blanco
    }


def _ocr_best_attempt(
    img: "Image.Image", page_num: int = 1, total: int = 1, dpi: int = 150
) -> str:
    """
    Prueba la secuencia de intentos OCR y devuelve el mejor resultado.
    Si la imagen parece invertida (fondo oscuro), la invierte primero.
    """
    from PIL import ImageOps  # noqa: PLC0415

    # Normalizar modo — Tesseract trabaja con RGB o L
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Analizar imagen
    analysis = _analyze_image(img)
    logger.info(
        f"Imagen p{page_num}/{total} @ {dpi}DPI — "
        f"modo={img.mode} size={img.size} "
        f"mean={analysis['mean']:.1f} std={analysis['std']:.1f}"
    )

    if analysis["likely_blank"]:
        logger.warning(f"Página {page_num} parece en blanco (std={analysis['std']:.1f})")
        return ""

    # Si la imagen parece invertida (blanco sobre negro), invertirla
    work_images = [img]
    if analysis["likely_inverted"]:
        logger.info(f"Imagen p{page_num} parece invertida — añadiendo versión invertida")
        inverted = ImageOps.invert(img.convert("L"))
        work_images = [inverted, img]   # primero la invertida

    best_text = ""
    best_chars = 0

    for work_img in work_images:
        for do_preprocess, lang, psm in _OCR_ATTEMPTS:
            try:
                proc_img = preprocess_image(work_img) if do_preprocess else work_img
                config = f"--psm {psm} --dpi {dpi}"
                text = pytesseract.image_to_string(proc_img, lang=lang, config=config)
                chars = len(text.strip())
                logger.info(
                    f"OCR p{page_num}/{total} — preproc={do_preprocess} "
                    f"lang={lang} psm={psm} → {chars} chars"
                )
                if chars > best_chars:
                    best_chars = chars
                    best_text = text
                # Solo detener si el resultado es claramente bueno
                if chars >= _CHARS_GOOD_ENOUGH:
                    logger.info(f"Resultado suficiente ({chars} chars ≥ {_CHARS_GOOD_ENOUGH}), deteniendo.")
                    return text
            except Exception as exc:
                logger.warning(f"OCR p{page_num} falló (lang={lang} psm={psm}): {exc}")

    if best_chars > 0:
        logger.info(f"Mejor resultado encontrado: {best_chars} chars en p{page_num}")
    else:
        logger.warning(
            f"Todos los intentos OCR dieron 0 chars en p{page_num} "
            f"(mean={analysis['mean']:.1f}, std={analysis['std']:.1f})."
        )
    return best_text


def preprocess_image(img: "Image.Image") -> "Image.Image":
    """Preprocesamiento conservador: escala de grises + contraste + nitidez."""
    from PIL import ImageOps, ImageFilter, ImageEnhance  # noqa: PLC0415

    img = img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = img.filter(ImageFilter.SHARPEN)

    w, h = img.size
    if max(w, h) < 2000:
        scale = 2 if max(w, h) < 1000 else 1.5
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    return img


def _extract_image(file_bytes: bytes) -> str:
    """Extrae texto de una imagen JPG o PNG. Fallback a Gemini Vision si Tesseract falla."""
    img = Image.open(io.BytesIO(file_bytes))
    text = _ocr_best_attempt(img)

    if not text.strip():
        logger.info("Tesseract no extrajo texto de la imagen. Intentando con Gemini Vision…")
        from app.services import gemini_service  # noqa: PLC0415
        # Usar los bytes originales (ya son JPEG o PNG nativos)
        mime = "image/jpeg" if file_bytes[:3] == b"\xff\xd8\xff" else "image/png"
        text = gemini_service.extract_text_from_image(file_bytes, mime_type=mime)

    return text
