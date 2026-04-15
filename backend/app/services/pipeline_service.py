"""Pipeline de procesamiento de documentos: OCR → NLP → actualizar BD."""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.document import Document, DocStatus
from app.models.category import Category
from app.services import ocr_service, nlp_service

logger = logging.getLogger("docmind")

CONFIDENCE_THRESHOLD = 0.70


def process_document(document_id: str, db: Session) -> None:
    """
    Ejecuta el pipeline completo para un documento:
      1. pending → processing
      2. OCR: extrae texto del archivo en MinIO
      3. NLP: clasifica contra las categorías de la organización
      4. Actualiza status → classified (score >= 0.70) o review (score < 0.70)

    Corre en background (FastAPI BackgroundTasks).
    Nunca propaga excepciones — los errores quedan loggeados y el doc pasa a 'error'.
    """
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Pipeline: documento '{document_id}' no encontrado en BD")
            return

        logger.info(f"Pipeline iniciado: doc={document_id} archivo='{doc.stored_path}'")

        # ── Paso 1: pending → processing ─────────────────────────────────────
        doc.status = DocStatus.processing
        doc.updated_at = datetime.utcnow()
        db.commit()

        # ── Paso 2: OCR ───────────────────────────────────────────────────────
        ocr_text = ocr_service.extract_text(doc.stored_path, doc.file_type)
        doc.ocr_text = ocr_text
        db.commit()

        # ── Paso 3: Categorías de la organización ────────────────────────────
        categories = (
            db.query(Category)
            .filter(Category.organization_id == doc.organization_id)
            .all()
        )
        category_names = [c.name for c in categories]

        # ── Paso 4: Clasificación NLP ─────────────────────────────────────────
        if ocr_text and category_names:
            predicted_name, score = nlp_service.classify_document(ocr_text, category_names)
            matched = next((c for c in categories if c.name == predicted_name), None)

            if matched:
                doc.category_id = matched.id
                doc.ai_confidence_score = score
                doc.status = (
                    DocStatus.classified if score >= CONFIDENCE_THRESHOLD else DocStatus.review
                )
            else:
                # El modelo retornó "Sin clasificar" o una etiqueta no reconocida
                doc.status = DocStatus.review
        else:
            # Sin texto o sin categorías: requiere revisión manual
            logger.info(
                f"Pipeline sin clasificación automática: "
                f"texto={'sí' if ocr_text else 'vacío'}, "
                f"categorías={len(category_names)}"
            )
            doc.status = DocStatus.review

        doc.updated_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Pipeline completado: doc={document_id} "
            f"status={doc.status.value} "
            f"score={doc.ai_confidence_score} "
            f"category_id={doc.category_id}"
        )

    except Exception as exc:
        logger.error(f"Error crítico en pipeline para doc={document_id}: {exc}", exc_info=True)
        # Intentar marcar el documento como error para que el usuario lo vea
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = DocStatus.error
                doc.updated_at = datetime.utcnow()
                db.commit()
        except Exception as inner_exc:
            logger.error(f"No se pudo actualizar status a 'error': {inner_exc}")
