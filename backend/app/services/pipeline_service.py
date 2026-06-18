"""Pipeline de procesamiento de documentos: OCR → DOCX → NLP → alertas → riesgo."""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.document import Document, DocStatus
from app.models.category import Category
from app.services import ocr_service, nlp_service, docx_service, minio_service
from app.services import alert_service, risk_service, gemini_service

logger = logging.getLogger("docmind")

CONFIDENCE_THRESHOLD = nlp_service.CONFIDENCE_THRESHOLD


def process_document(document_id: str, db: Session) -> None:
    """
    Pipeline completo para un documento:
      1. pending → processing
      2. OCR
      3. Resumen automático (ai_summary)
      4. Generación .docx
      5. NLP clasificación (classified si score ≥ umbral, review si no)
      6. Alertas de vencimiento
      7. Evaluación de riesgo
    """
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Pipeline: documento '{document_id}' no encontrado en BD")
            return

        logger.info(f"Pipeline iniciado: doc={document_id} archivo='{doc.stored_path}'")

        # ── 1: pending → processing ───────────────────────────────────────────
        doc.status = DocStatus.processing
        doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()

        # ── 2: OCR ────────────────────────────────────────────────────────────
        ocr_text = ocr_service.extract_text(doc.stored_path, doc.file_type)
        doc.ocr_text = ocr_text
        db.commit()

        if not ocr_text:
            logger.warning(f"Pipeline: OCR vacío para doc={document_id} → error")
            doc.status = DocStatus.error
            doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            return

        # Umbral de calidad: si el OCR extrajo muy pocos caracteres (< 100)
        # probablemente la imagen es de baja calidad y el texto es ilegible.
        # En vez de intentar clasificar basura con el NLP (que puede tardar
        # minutos en cargar el modelo), ir directo a review para revisión manual.
        if len(ocr_text) < 100:
            logger.warning(
                f"Pipeline: OCR extrajo solo {len(ocr_text)} chars para "
                f"doc={document_id} (umbral mínimo: 100). "
                "Calidad insuficiente para clasificación automática → review."
            )
            doc.ai_summary = ocr_text[:200] if ocr_text else None
            doc.status = DocStatus.review
            doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            return

        # ── 3: Resumen automático con Gemini ─────────────────────────────────
        doc.ai_summary = gemini_service.summarize_document(
            ocr_text, doc_name=doc.original_filename
        )
        db.commit()

        # ── 4: Generación del .docx ───────────────────────────────────────────
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
        except Exception as docx_exc:
            logger.error(f"Pipeline: error generando .docx para doc={document_id}: {docx_exc}", exc_info=True)

        # ── 5: Categorías y clasificación NLP ─────────────────────────────────
        categories = (
            db.query(Category)
            .filter(Category.organization_id == doc.organization_id)
            .all()
        )
        category_names = [c.name for c in categories]

        if not category_names:
            logger.info(
                f"Pipeline: sin categorías en la org → doc={document_id} en 'review'. "
                "Motivo: no existen categorías en la organización."
            )
            from app.services.audit_service import log_action
            from app.models.audit_log import AuditAction
            log_action(
                db=db,
                user_id=doc.uploaded_by,
                action=AuditAction.upload,
                document_id=doc.id,
                detail={"pipeline_review_reason": "no_categories_in_org"},
            )
            doc.status = DocStatus.review
            doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            return

        predicted_name, score = nlp_service.classify_document(ocr_text, category_names)
        matched = next((c for c in categories if c.name == predicted_name), None)

        if matched is None:
            matched = categories[0]
            score = 0.0
            logger.warning(f"Pipeline: etiqueta NLP no coincide → fallback '{matched.name}'")

        doc.category_id = matched.id
        doc.ai_confidence_score = score

        if score < CONFIDENCE_THRESHOLD:
            doc.status = DocStatus.review
            logger.info(f"Pipeline: score bajo ({score:.2f}) → review. Doc={document_id}")
        else:
            doc.status = DocStatus.classified

        doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()

        # ── 6: Alertas de vencimiento ─────────────────────────────────────────
        try:
            alerts = alert_service.detect_expiry_dates(ocr_text)
            if alerts:
                alert_service.persist_alerts(db, document_id, doc.organization_id, alerts)
        except Exception as alert_exc:
            logger.error(f"Pipeline: error en alertas para doc={document_id}: {alert_exc}", exc_info=True)

        # ── 7: Evaluación de riesgo ───────────────────────────────────────────
        try:
            risk = risk_service.evaluate_risk(
                db=db,
                organization_id=doc.organization_id,
                category_id=doc.category_id,
                ocr_text=ocr_text,
                file_size_kb=doc.file_size_kb,
            )
            doc.risk_level = risk
            db.commit()
        except Exception as risk_exc:
            logger.error(f"Pipeline: error en riesgo para doc={document_id}: {risk_exc}", exc_info=True)

        logger.info(
            f"Pipeline completado: doc={document_id} status={doc.status.value} "
            f"score={doc.ai_confidence_score} category='{matched.name}' risk={doc.risk_level}"
        )

    except Exception as exc:
        logger.error(f"Error crítico en pipeline doc={document_id}: {exc}", exc_info=True)
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = DocStatus.error
                doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                db.commit()
        except Exception as inner:
            logger.error(f"No se pudo marcar error: {inner}")


