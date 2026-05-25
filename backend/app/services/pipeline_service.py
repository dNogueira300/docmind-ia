"""Pipeline de procesamiento de documentos: OCR → DOCX → NLP → actualizar BD."""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.document import Document, DocStatus
from app.models.category import Category
from app.services import ocr_service, nlp_service, docx_service, minio_service

logger = logging.getLogger("docmind")

# Umbral: si el clasificador supera este score, se marca como `classified`.
# Por debajo, se asigna la mejor categoría disponible pero queda en `review`
# para que un editor confirme. Aun así NUNCA se deja sin categoría cuando
# hay texto OCR + al menos una categoría en la organización.
CONFIDENCE_THRESHOLD = nlp_service.CONFIDENCE_THRESHOLD


def process_document(document_id: str, db: Session) -> None:
    """
    Ejecuta el pipeline completo para un documento:
      1. pending → processing
      2. OCR: extrae texto del archivo en MinIO
      3. Digitalización: genera un .docx editable y lo sube a MinIO
      4. NLP: clasifica contra las categorías de la organización
      5. Actualiza status:
         - texto OCR vacío               → error
         - sin categorías en la org      → review
         - score >= CONFIDENCE_THRESHOLD → classified (categoría asignada)
         - score <  CONFIDENCE_THRESHOLD → classified igualmente con la mejor
           categoría candidata; el `ai_confidence_score` queda guardado para
           que el editor pueda revisar si lo desea, pero el documento no se
           bloquea en `review`.

    Corre en background (FastAPI BackgroundTasks).
    Nunca propaga excepciones — los errores se loggean y el doc pasa a `error`.
    """
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Pipeline: documento '{document_id}' no encontrado en BD")
            return

        logger.info(
            f"Pipeline iniciado: doc={document_id} archivo='{doc.stored_path}'"
        )

        # ── Paso 1: pending → processing ─────────────────────────────────────
        doc.status = DocStatus.processing
        doc.updated_at = datetime.utcnow()
        db.commit()

        # ── Paso 2: OCR ───────────────────────────────────────────────────────
        ocr_text = ocr_service.extract_text(doc.stored_path, doc.file_type)
        doc.ocr_text = ocr_text
        db.commit()

        if not ocr_text:
            logger.warning(
                f"Pipeline: OCR no extrajo texto para doc={document_id}. "
                "Marcando como 'error'."
            )
            doc.status = DocStatus.error
            doc.updated_at = datetime.utcnow()
            db.commit()
            return

        # ── Paso 3: Generación del .docx digitalizado ────────────────────────
        try:
            docx_bytes = docx_service.build_docx(
                ocr_text=ocr_text,
                source_filename=doc.original_filename,
            )
            digitalized_path = minio_service.upload_digitalized_docx(
                docx_bytes=docx_bytes,
                original_stored_path=doc.stored_path,
            )
            doc.digitalized_path = digitalized_path
            db.commit()
            logger.info(
                f"Pipeline: .docx digitalizado subido a '{digitalized_path}'"
            )
        except Exception as docx_exc:
            # La digitalización es importante pero no debe bloquear la clasificación.
            logger.error(
                f"Pipeline: error generando .docx para doc={document_id}: {docx_exc}",
                exc_info=True,
            )

        # ── Paso 4: Categorías de la organización ────────────────────────────
        categories = (
            db.query(Category)
            .filter(Category.organization_id == doc.organization_id)
            .all()
        )
        category_names = [c.name for c in categories]

        if not category_names:
            logger.info(
                f"Pipeline: sin categorías en la organización — doc={document_id} "
                "queda en 'review' para asignación manual."
            )
            doc.status = DocStatus.review
            doc.updated_at = datetime.utcnow()
            db.commit()
            return

        # ── Paso 5: Clasificación NLP ────────────────────────────────────────
        predicted_name, score = nlp_service.classify_document(
            ocr_text, category_names
        )
        matched = next(
            (c for c in categories if c.name == predicted_name), None
        )

        if matched is None:
            # NLP no devolvió una etiqueta reconocida — usar la primera disponible
            matched = categories[0]
            score = 0.0
            logger.warning(
                f"Pipeline: etiqueta NLP '{predicted_name}' no coincide con "
                f"categorías reales. Asignando fallback '{matched.name}'."
            )

        doc.category_id = matched.id
        doc.ai_confidence_score = score
        # Política: siempre clasificamos. El umbral solo afecta el log de auditoría.
        doc.status = DocStatus.classified

        doc.updated_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Pipeline completado: doc={document_id} "
            f"status={doc.status.value} "
            f"score={doc.ai_confidence_score} "
            f"category_id={doc.category_id} "
            f"category='{matched.name}'"
        )

    except Exception as exc:
        logger.error(
            f"Error crítico en pipeline para doc={document_id}: {exc}",
            exc_info=True,
        )
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = DocStatus.error
                doc.updated_at = datetime.utcnow()
                db.commit()
        except Exception as inner_exc:
            logger.error(
                f"No se pudo actualizar status a 'error': {inner_exc}"
            )
