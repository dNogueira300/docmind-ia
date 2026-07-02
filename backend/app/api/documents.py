"""Endpoints de documentos: subida, listado, detalle, reclasificación, eliminación."""
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Annotated, Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, HTTPException,
    UploadFile, File, Request, status, Query,
)

logger = logging.getLogger("docmind.documents")
from sqlalchemy import func, or_, desc, case
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import (
    require_role, get_current_user, get_active_organization_id,
)
from app.models.user import User
from app.models.document import Document, DocStatus
from app.models.audit_log import AuditAction
from app.schemas.document import (
    DocumentResponse, DocumentListResponse, DocumentReclassify, DocumentSearchResult,
)
from app.services import minio_service, gemini_service
from app.services.audit_service import log_action
from app.services.pipeline_service import process_document

router = APIRouter(prefix="/documents", tags=["Documentos"])

AnyRole = Annotated[User, Depends(get_current_user)]
EditorOrAdmin = Annotated[User, Depends(require_role("admin", "editor"))]
AdminOnly = Annotated[User, Depends(require_role("admin"))]

# Tipos de archivo permitidos — validados por magic bytes
ALLOWED_MAGIC: dict[bytes, str] = {
    b"%PDF": "pdf",
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG": "png",
}
MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


ALLOWED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


def _detect_file_type(header: bytes, ip: str | None = None, filename: str | None = None) -> str:
    """Detecta el tipo de archivo por magic bytes. Lanza 422 si no es permitido."""
    for magic, ftype in ALLOWED_MAGIC.items():
        if header.startswith(magic):
            return ftype
    logger.warning(
        "SEGURIDAD | archivo rechazado | ip=%s | filename=%s | motivo=magic_bytes_invalidos",
        ip,
        filename,
    )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Tipo de archivo no permitido. Solo se aceptan PDF, JPG y PNG.",
    )


@router.get("/", response_model=list[DocumentListResponse], summary="Listar documentos")
async def list_documents(
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    category_id: Optional[UUID] = Query(None),
    doc_status: Optional[DocStatus] = Query(None, alias="status"),
    file_type: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    uploaded_by: Optional[UUID] = Query(None),
) -> list[dict]:
    """Lista documentos de la organización con filtros opcionales."""
    from app.models.user import User as UserModel  # noqa: PLC0415

    q = (
        db.query(Document)
        .options(joinedload(Document.uploader))
        .filter(Document.organization_id == organization_id)
    )
    if category_id:
        q = q.filter(Document.category_id == category_id)
    if doc_status:
        q = q.filter(Document.status == doc_status)
    if file_type:
        q = q.filter(Document.file_type == file_type)
    if from_date:
        q = q.filter(Document.created_at >= from_date)
    if to_date:
        q = q.filter(Document.created_at <= to_date)
    if uploaded_by:
        q = q.filter(Document.uploaded_by == uploaded_by)

    docs = q.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

    # Serializar manualmente para incluir uploader_name
    result = []
    for d in docs:
        item = {
            "id": d.id,
            "organization_id": d.organization_id,
            "category_id": d.category_id,
            "uploaded_by": d.uploaded_by,
            "uploader_name": d.uploader.name if d.uploader else None,
            "original_filename": d.original_filename,
            "file_type": d.file_type,
            "file_size_kb": d.file_size_kb,
            "ai_summary": d.ai_summary,
            "ai_confidence_score": d.ai_confidence_score,
            "risk_level": d.risk_level,
            "status": d.status,
            "has_digitalized": bool(d.digitalized_path),
            "has_ocr_pdf": bool(d.ocr_pdf_path),
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        }
        result.append(item)
    return result


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Subir documento",
)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: EditorOrAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> Document:
    """
    Sube un documento a MinIO y crea el registro en BD con status=pending.
    El OCR y la clasificación IA corren en background (Hito 3).
    """
    ip = request.client.host if request.client else None
    filename = file.filename or "documento"

    # Validar Content-Type declarado
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(
            "SEGURIDAD | archivo rechazado | ip=%s | filename=%s | motivo=content_type_invalido | content_type=%s",
            ip,
            filename,
            file.content_type,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tipo de archivo no permitido. Solo se aceptan PDF, JPG y PNG.",
        )

    # Leer los primeros 12 bytes para detectar tipo por magic bytes
    header = await file.read(12)

    if len(header) == 0:
        logger.warning(
            "SEGURIDAD | archivo rechazado | ip=%s | filename=%s | motivo=archivo_vacio",
            ip,
            filename,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no puede estar vacío.",
        )

    file_type = _detect_file_type(header, ip=ip, filename=filename)

    # Leer el resto del archivo
    rest = await file.read()
    file_data = header + rest

    if len(file_data) > MAX_SIZE_BYTES:
        logger.warning(
            "SEGURIDAD | archivo rechazado | ip=%s | filename=%s | motivo=excede_20mb | size_bytes=%d",
            ip,
            filename,
            len(file_data),
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el límite de 20 MB",
        )

    document_id = uuid4()
    file_size_kb = len(file_data) // 1024

    # Límite de almacenamiento según el plan de la organización.
    from app.services import plan_service  # noqa: PLC0415
    from app.core.plans import plan_limits  # noqa: PLC0415
    org = plan_service.get_org(db, organization_id)
    if org and not plan_service.can_store(db, org, file_size_kb):
        limit_mb = plan_limits(plan_service.effective_plan(org))["max_storage_mb"]
        logger.warning(
            "Org %s alcanzó el límite de almacenamiento (%s MB)", organization_id, limit_mb
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Alcanzaste el límite de almacenamiento de tu plan ({limit_mb} MB). "
                "Elimina documentos o mejora tu plan."
            ),
        )

    # Subir a MinIO
    stored_path = minio_service.upload_file(
        file_data=file_data,
        filename=file.filename or "documento",
        content_type=file.content_type or "application/octet-stream",
        organization_id=organization_id,
        document_id=document_id,
    )

    # Crear registro en BD
    doc = Document(
        id=document_id,
        organization_id=organization_id,
        uploaded_by=current_user.id,
        original_filename=file.filename or "documento",
        stored_path=stored_path,
        file_type=file_type,
        file_size_kb=file_size_kb,
        status=DocStatus.pending,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Auditoría
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.upload,
        document_id=doc.id,
        detail={"filename": doc.original_filename, "size_kb": file_size_kb},
        ip_address=ip,
    )

    # Disparar pipeline OCR + NLP en background
    background_tasks.add_task(process_document, str(doc.id), db)

    return doc


@router.get(
    "/search",
    response_model=list[DocumentSearchResult],
    summary="Búsqueda combinada (nombre + contenido + fuzzy) con fragmento de texto",
)
async def search_documents(
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
    q: str = Query(
        default="",
        description=(
            "Texto a buscar. Coincide por: (1) nombre del archivo, "
            "(2) contenido OCR via full-text en español, "
            "(3) similitud fuzzy (pg_trgm) tolerante a errores tipográficos."
        ),
    ),
    semantic: bool = Query(
        default=False,
        description=(
            "Si es true, re-rankea los resultados del FTS por relevancia semántica "
            "con Gemini (más lento). Si Gemini falla, mantiene el orden FTS."
        ),
    ),
    skip: int = 0,
    limit: int = 20,
) -> list[DocumentSearchResult]:
    """
    Búsqueda inteligente que combina tres estrategias y las une por OR:

    1. **Nombre del archivo** (ILIKE %q%): si el archivo se llama `1234.pdf`,
       buscar `1234` lo encuentra.
    2. **Contenido OCR**: PostgreSQL full-text search en español sobre `ocr_text`
       (índice GIN existente). Encuentra "contrato" dentro del documento aunque
       el archivo se llame `1234.pdf`.
    3. **Fuzzy / tolerante a errores**: similitud trigram (`pg_trgm`) SOLO sobre
       el nombre del archivo. Si el usuario escribe `conratro`, encuentra
       `contrato.pdf`. En el contenido NO se aplica fuzzy: si la palabra/frase
       no aparece en el texto, el documento no se devuelve.

    Resultados ordenados por mejor relevancia combinada.
    """
    query_str = q.strip()
    if not query_str:
        return []

    org_id = organization_id
    like_pattern = f"%{query_str}%"
    # Tolerancia a errores tipográficos SOLO en el nombre del archivo. En el
    # contenido NO se aplica fuzzy: si la palabra/frase no aparece en el texto,
    # el documento no debe salir (antes un umbral bajo hacía match con todo).
    name_fuzzy_threshold = 0.45

    tsquery = func.plainto_tsquery("spanish", query_str)
    tsvector = func.to_tsvector("spanish", func.coalesce(Document.ocr_text, ""))

    # Fragmento del texto donde coincide la query (línea de contexto). ts_headline
    # devuelve una porción del ocr_text con los términos marcados entre «…».
    snippet_expr = func.ts_headline(
        "spanish",
        func.coalesce(Document.ocr_text, ""),
        tsquery,
        "MaxFragments=1, MinWords=6, MaxWords=25, StartSel=«, StopSel=», "
        "FragmentDelimiter= … ",
    )

    # Scores parciales — se suman para ordenar (mayor primero).
    # Boost: match exacto de substring en el nombre vale 1.0 fijo.
    name_score = case(
        (Document.original_filename.ilike(like_pattern), 1.0),
        else_=func.similarity(Document.original_filename, query_str),
    )
    fts_score = func.coalesce(func.ts_rank(tsvector, tsquery), 0.0)
    # Boost si la frase aparece literal (substring) en el contenido.
    content_like_score = case(
        (func.coalesce(Document.ocr_text, "").ilike(like_pattern), 0.5),
        else_=0.0,
    )

    # Condiciones (cualquiera basta) — todas exigen que el término APAREZCA:
    #   1. substring en el nombre     2. nombre similar (typos)
    #   3. full-text en el contenido  4. substring literal en el contenido
    cond_name_like = Document.original_filename.ilike(like_pattern)
    cond_name_fuzzy = func.similarity(
        Document.original_filename, query_str
    ) > name_fuzzy_threshold
    cond_fts = tsvector.op("@@")(tsquery)
    cond_content_like = func.coalesce(Document.ocr_text, "").ilike(like_pattern)

    rows = (
        db.query(Document, snippet_expr.label("snippet"))
        .options(joinedload(Document.uploader))
        .filter(
            Document.organization_id == org_id,
            or_(cond_name_like, cond_name_fuzzy, cond_fts, cond_content_like),
        )
        .order_by(
            desc(name_score + fts_score + content_like_score),
            Document.created_at.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    def _clean_snippet(doc: Document, raw: Optional[str]) -> Optional[str]:
        # 1. ts_headline resaltó el término (match FTS sobre el contenido).
        if raw and "«" in raw:
            return raw.strip()
        # 2. La frase aparece literal en el contenido pero FTS no la resaltó
        #    (p.ej. frases con stopwords): construir el fragmento a mano.
        text = doc.ocr_text or ""
        pos = text.lower().find(query_str.lower())
        if pos != -1:
            start = max(0, pos - 40)
            end = min(len(text), pos + len(query_str) + 80)
            rel = pos - start
            frag = text[start:end]
            frag = (
                frag[:rel] + "«" + frag[rel:rel + len(query_str)] + "»"
                + frag[rel + len(query_str):]
            )
            frag = " ".join(frag.split())  # colapsar saltos/espacios del OCR
            return ("… " if start > 0 else "") + frag + (" …" if end < len(text) else "")
        # 3. Coincidió solo por el nombre del archivo: mostrar el resumen como
        #    contexto (no hay fragmento de contenido que resaltar).
        return (doc.ai_summary or "").strip() or None

    results = [
        DocumentSearchResult(
            id=doc.id,
            organization_id=doc.organization_id,
            category_id=doc.category_id,
            uploaded_by=doc.uploaded_by,
            uploader_name=doc.uploader.name if doc.uploader else None,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size_kb=doc.file_size_kb,
            ai_summary=doc.ai_summary,
            ai_confidence_score=doc.ai_confidence_score,
            risk_level=doc.risk_level,
            status=doc.status,
            has_digitalized=doc.has_digitalized,
            has_ocr_pdf=doc.has_ocr_pdf,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            snippet=_clean_snippet(doc, snippet),
        )
        for doc, snippet in rows
    ]

    # Re-ranking semántico opcional con Gemini (solo si el plan lo incluye y hay
    # créditos; si no, se mantiene el orden FTS sin error).
    from app.services import plan_service  # noqa: PLC0415
    _sem_org = plan_service.get_org(db, organization_id) if semantic and results else None
    if (
        semantic and results and _sem_org
        and plan_service.has_feature(_sem_org, "semantic_search")
        and plan_service.consume_ai_credit(db, _sem_org)
    ):
        order = gemini_service.rerank_semantic(
            query_str,
            [
                {"id": str(r.id), "filename": r.original_filename, "snippet": r.snippet or ""}
                for r in results
            ],
        )
        if order:
            by_id = {str(r.id): r for r in results}
            reordered = [by_id[i] for i in order if i in by_id]
            # Anexar los que Gemini omitió, preservando su orden FTS.
            seen = set(order)
            reordered += [r for r in results if str(r.id) not in seen]
            results = reordered

    return results


@router.get("/{document_id}", response_model=DocumentResponse, summary="Ver documento")
async def get_document(
    document_id: UUID,
    request: Request,
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> Document:
    """Retorna el detalle completo de un documento, incluyendo ocr_text."""
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Auditoría
    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.view,
        document_id=doc.id,
        ip_address=ip,
    )

    return doc


@router.get(
    "/{document_id}/download-url",
    summary="Obtener URL de descarga del archivo original",
)
async def get_download_url(
    document_id: UUID,
    request: Request,
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """Genera una URL firmada temporal (1 hora) para descargar el archivo original."""
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    url = minio_service.get_presigned_url(
        doc.stored_path,
        response_filename=doc.original_filename,
    )

    # Auditoría
    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.download,
        document_id=doc.id,
        ip_address=ip,
    )

    return {"download_url": url, "expires_in_seconds": 3600}


@router.get(
    "/{document_id}/preview-url",
    summary="URL firmada inline para vista previa del archivo original",
)
async def get_preview_url(
    document_id: UUID,
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """
    URL firmada para mostrar el archivo original embebido (iframe / img tag).
    No registra auditoría de descarga — solo es para preview en el panel detalle.
    """
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    url = minio_service.get_presigned_url(doc.stored_path)
    return {
        "preview_url": url,
        "file_type": doc.file_type,
        "expires_in_seconds": 3600,
    }


@router.get(
    "/{document_id}/digitalized-url",
    summary="URL firmada para descargar el .docx digitalizado",
)
async def get_digitalized_url(
    document_id: UUID,
    request: Request,
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """
    Devuelve la URL firmada del archivo .docx generado tras el OCR.
    Si la digitalización aún no terminó, responde 404.
    """
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not doc.digitalized_path:
        raise HTTPException(
            status_code=404,
            detail="El documento aún no ha sido digitalizado.",
        )

    # Nombre amigable para la descarga
    base_name = doc.original_filename.rsplit(".", 1)[0] or "documento"
    download_name = f"{base_name}.docx"

    url = minio_service.get_presigned_url(
        doc.digitalized_path,
        response_filename=download_name,
    )

    # Auditoría: cuenta como descarga
    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.download,
        document_id=doc.id,
        detail={"type": "digitalized_docx"},
        ip_address=ip,
    )

    return {"download_url": url, "expires_in_seconds": 3600}


@router.get(
    "/{document_id}/ocr-pdf-url",
    summary="URL firmada para descargar el PDF con capa de texto OCR (editable)",
)
async def get_ocr_pdf_url(
    document_id: UUID,
    request: Request,
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """
    Devuelve la URL firmada del PDF con capa de texto OCR (mantiene la apariencia
    del original pero el texto es seleccionable/editable). 404 si aún no existe.
    """
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not doc.ocr_pdf_path:
        raise HTTPException(
            status_code=404,
            detail="El documento aún no tiene PDF con OCR.",
        )

    base_name = doc.original_filename.rsplit(".", 1)[0] or "documento"
    download_name = f"{base_name}.ocr.pdf"

    url = minio_service.get_presigned_url(
        doc.ocr_pdf_path,
        response_filename=download_name,
    )

    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.download,
        document_id=doc.id,
        detail={"type": "ocr_pdf"},
        ip_address=ip,
    )

    return {"download_url": url, "expires_in_seconds": 3600}


@router.put(
    "/{document_id}/category",
    response_model=DocumentResponse,
    summary="Reclasificar documento",
)
async def reclassify_document(
    document_id: UUID,
    data: DocumentReclassify,
    request: Request,
    current_user: EditorOrAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> Document:
    """Reclasifica manualmente un documento asignándole una categoría."""
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Verificar que la categoría pertenece a la misma organización
    from app.models.category import Category

    category = (
        db.query(Category)
        .filter(
            Category.id == data.category_id,
            Category.organization_id == organization_id,
        )
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    old_category_id = str(doc.category_id) if doc.category_id else None
    doc.category_id = data.category_id
    doc.status = DocStatus.classified
    doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(doc)

    # Auditoría
    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.reclassify,
        document_id=doc.id,
        detail={
            "from_category": old_category_id,
            "to_category": str(data.category_id),
        },
        ip_address=ip,
    )

    return doc


@router.patch(
    "/{document_id}/reprocess",
    response_model=DocumentResponse,
    summary="Reprocesar documento (relanzar pipeline OCR + NLP)",
)
async def reprocess_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: EditorOrAdmin,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> Document:
    """
    Relanza el pipeline OCR + NLP sobre un documento en estado 'review' o 'error'.
    Responde inmediatamente con el documento en estado 'pending'.
    """
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if doc.status not in (DocStatus.review, DocStatus.error):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden reprocesar documentos en estado 'review' o 'error'",
        )

    doc.status = DocStatus.pending
    doc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(process_document, str(doc.id), db)
    return doc


@router.get(
    "/stats/by-category",
    summary="Conteo de documentos por categoría",
)
async def stats_by_category(
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    from app.models.category import Category

    rows = (
        db.query(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            Category.color.label("color"),
            func.count(Document.id).label("count"),
        )
        .outerjoin(Document, (Document.category_id == Category.id) & (Document.organization_id == organization_id))
        .filter(Category.organization_id == organization_id)
        .group_by(Category.id, Category.name, Category.color)
        .order_by(desc(func.count(Document.id)))
        .all()
    )
    return [
        {"category_id": str(r.category_id), "category_name": r.category_name, "color": r.color, "count": r.count}
        for r in rows
    ]


@router.get(
    "/stats/by-user",
    summary="Conteo de documentos por usuario",
)
async def stats_by_user(
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    from app.models.user import User as UserModel

    rows = (
        db.query(
            UserModel.id.label("user_id"),
            UserModel.name.label("user_name"),
            func.count(Document.id).label("count"),
        )
        .outerjoin(Document, (Document.uploaded_by == UserModel.id) & (Document.organization_id == organization_id))
        .filter(UserModel.organization_id == organization_id)
        .group_by(UserModel.id, UserModel.name)
        .order_by(desc(func.count(Document.id)))
        .all()
    )
    return [
        {"user_id": str(r.user_id), "user_name": r.user_name, "count": r.count}
        for r in rows
    ]


@router.get(
    "/stats/by-risk",
    summary="Conteo de documentos por nivel de riesgo",
)
async def stats_by_risk(
    current_user: AnyRole,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = (
        db.query(
            Document.risk_level.label("risk_level"),
            func.count(Document.id).label("count"),
        )
        .filter(Document.organization_id == organization_id)
        .group_by(Document.risk_level)
        .all()
    )
    return [{"risk_level": r.risk_level or "low", "count": r.count} for r in rows]


@router.delete("/{document_id}", summary="Eliminar documento")
async def delete_document(
    document_id: UUID,
    request: Request,
    current_user: AdminOnly,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    """
    Marca el documento como eliminado (status=error) y lo elimina de MinIO.
    Los registros de audit_log se conservan (ON DELETE SET NULL).
    """
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Auditoría antes de eliminar
    ip = request.client.host if request.client else None
    log_action(
        db=db,
        user_id=current_user.id,
        action=AuditAction.delete,
        document_id=doc.id,
        detail={"filename": doc.original_filename},
        ip_address=ip,
    )

    # Eliminar archivo de MinIO
    minio_service.delete_file(doc.stored_path)

    # Eliminar registro de BD
    db.delete(doc)
    db.commit()

    return {"detail": f"Documento '{doc.original_filename}' eliminado correctamente"}
