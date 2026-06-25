"""Pipeline de procesamiento de documentos: OCR → DOCX → NLP → alertas → riesgo."""
import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document, DocStatus
from app.models.category import Category
from app.models.category_suggestion import CategorySuggestion, SuggestionStatus
from app.services import ocr_service, nlp_service, docx_service, minio_service
from app.services import alert_service, risk_service, gemini_service

logger = logging.getLogger("docmind")


def _persist_suggestion(
    db: Session, doc: Document, name: str, confidence: float
) -> None:
    """Guarda una sugerencia de categoría PENDIENTE (sin duplicar pendientes)."""
    if not name or not name.strip():
        return
    name = name.strip()

    # Dedupe: ya existe una categoría con ese nombre, o una sugerencia pendiente.
    exists_cat = (
        db.query(Category)
        .filter(
            Category.organization_id == doc.organization_id,
            func.lower(Category.name) == name.lower(),
        )
        .first()
    )
    if exists_cat:
        return
    already = (
        db.query(CategorySuggestion)
        .filter(
            CategorySuggestion.organization_id == doc.organization_id,
            CategorySuggestion.status == SuggestionStatus.pending,
            func.lower(CategorySuggestion.suggested_name) == name.lower(),
        )
        .first()
    )
    if already:
        return

    db.add(
        CategorySuggestion(
            organization_id=doc.organization_id,
            document_id=doc.id,
            suggested_name=name,
            confidence=confidence,
        )
    )
    db.commit()
    logger.info(f"Pipeline: sugerencia de categoría '{name}' creada para doc={doc.id}")

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

        # ── 4b: PDF con capa de texto OCR (apariencia original + texto editable) ─
        try:
            ocr_pdf_bytes = ocr_service.build_searchable_pdf(
                doc.stored_path, doc.file_type
            )
            if ocr_pdf_bytes:
                doc.ocr_pdf_path = minio_service.upload_searchable_pdf(
                    pdf_bytes=ocr_pdf_bytes,
                    original_stored_path=doc.stored_path,
                )
                db.commit()
                logger.info(f"Pipeline: PDF con OCR generado para doc={document_id}")
        except Exception as ocrpdf_exc:
            logger.error(
                f"Pipeline: error generando PDF con OCR para doc={document_id}: {ocrpdf_exc}",
                exc_info=True,
            )

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
            # Sin categorías aún: proponer una a partir del documento.
            try:
                result = gemini_service.classify_or_suggest(
                    ocr_text, [], doc_name=doc.original_filename
                )
                if result and result["new_category"]:
                    _persist_suggestion(db, doc, result["new_category"], result["confidence"])
            except Exception as sug_exc:
                logger.error(
                    f"Pipeline: error sugiriendo categoría doc={document_id}: {sug_exc}",
                    exc_info=True,
                )
            return

        # ── Clasificación: Gemini decide si encaja o sugiere categoría nueva ──
        result = gemini_service.classify_or_suggest(
            ocr_text, category_names, doc_name=doc.original_filename
        )

        if result is None:
            # Fallback: Gemini no disponible → heurística/zero-shot.
            predicted_name, score = nlp_service.classify_document(
                ocr_text, category_names
            )
            matched = next((c for c in categories if c.name == predicted_name), None) or categories[0]
            doc.category_id = matched.id
            doc.ai_confidence_score = score
            doc.status = DocStatus.classified if score >= CONFIDENCE_THRESHOLD else DocStatus.review
        elif result["category"]:
            # Encaja en una categoría existente.
            matched = next(c for c in categories if c.name == result["category"])
            score = result["confidence"]
            doc.category_id = matched.id
            doc.ai_confidence_score = score
            doc.status = DocStatus.classified if score >= CONFIDENCE_THRESHOLD else DocStatus.review
            logger.info(
                f"Pipeline: clasificado '{matched.name}' (score={score:.2f}) doc={document_id}"
            )
        else:
            # NO encaja en ninguna → no forzar: sin categoría, review + sugerencia.
            doc.category_id = None
            doc.ai_confidence_score = result["confidence"]
            doc.status = DocStatus.review
            logger.info(
                f"Pipeline: no encaja en categorías existentes → review + sugerencia "
                f"'{result['new_category']}' doc={document_id}"
            )
            try:
                if result["new_category"]:
                    _persist_suggestion(db, doc, result["new_category"], result["confidence"])
            except Exception as sug_exc:
                logger.error(
                    f"Pipeline: error sugiriendo categoría doc={document_id}: {sug_exc}",
                    exc_info=True,
                )

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

        category_label = doc.category.name if doc.category_id and doc.category else "sin categoría"
        logger.info(
            f"Pipeline completado: doc={document_id} status={doc.status.value} "
            f"score={doc.ai_confidence_score} category='{category_label}' risk={doc.risk_level}"
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


