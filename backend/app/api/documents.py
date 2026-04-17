"""Endpoints de documentos: subida, listado, detalle, reclasificación, eliminación."""
import logging
from datetime import datetime
from uuid import UUID, uuid4
from typing import Annotated, Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, HTTPException,
    UploadFile, File, Request, status, Query,
)

logger = logging.getLogger("docmind.documents")
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role, get_current_user
from app.models.user import User
from app.models.document import Document, DocStatus
from app.models.audit_log import AuditAction
from app.schemas.document import DocumentResponse, DocumentListResponse, DocumentReclassify
from app.services import minio_service
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
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    category_id: Optional[UUID] = Query(None),
    doc_status: Optional[DocStatus] = Query(None, alias="status"),
    file_type: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
) -> list[Document]:
    """Lista documentos de la organización con filtros opcionales."""
    q = db.query(Document).filter(
        Document.organization_id == current_user.organization_id
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

    return q.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()


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

    # Subir a MinIO
    stored_path = minio_service.upload_file(
        file_data=file_data,
        filename=file.filename or "documento",
        content_type=file.content_type or "application/octet-stream",
        organization_id=current_user.organization_id,
        document_id=document_id,
    )

    # Crear registro en BD
    doc = Document(
        id=document_id,
        organization_id=current_user.organization_id,
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


@router.get("/search", response_model=list[DocumentListResponse], summary="Búsqueda full-text")
async def search_documents(
    current_user: AnyRole,
    db: Session = Depends(get_db),
    q: str = Query(default="", description="Texto a buscar en el contenido de los documentos"),
    skip: int = 0,
    limit: int = 20,
) -> list[Document]:
    """
    Búsqueda semántica sobre ocr_text usando PostgreSQL full-text search (índice GIN).
    Retorna documentos con status 'classified' o 'review' de la organización del usuario.
    """
    if not q.strip():
        return []

    tsquery = func.plainto_tsquery("spanish", q)
    tsvector = func.to_tsvector("spanish", Document.ocr_text)

    return (
        db.query(Document)
        .filter(
            Document.organization_id == current_user.organization_id,
            Document.status.in_([DocStatus.classified, DocStatus.review]),
            Document.ocr_text.isnot(None),
            tsvector.op("@@")(tsquery),
        )
        .order_by(func.ts_rank(tsvector, tsquery).desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{document_id}", response_model=DocumentResponse, summary="Ver documento")
async def get_document(
    document_id: UUID,
    request: Request,
    current_user: AnyRole,
    db: Session = Depends(get_db),
) -> Document:
    """Retorna el detalle completo de un documento, incluyendo ocr_text."""
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == current_user.organization_id,
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
    summary="Obtener URL de descarga",
)
async def get_download_url(
    document_id: UUID,
    request: Request,
    current_user: AnyRole,
    db: Session = Depends(get_db),
) -> dict:
    """Genera una URL firmada temporal (1 hora) para descargar el archivo."""
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    url = minio_service.get_presigned_url(doc.stored_path)

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
    db: Session = Depends(get_db),
) -> Document:
    """Reclasifica manualmente un documento asignándole una categoría."""
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == current_user.organization_id,
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
            Category.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    old_category_id = str(doc.category_id) if doc.category_id else None
    doc.category_id = data.category_id
    doc.status = DocStatus.classified
    doc.updated_at = datetime.utcnow()
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


@router.delete("/{document_id}", summary="Eliminar documento")
async def delete_document(
    document_id: UUID,
    request: Request,
    current_user: AdminOnly,
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
            Document.organization_id == current_user.organization_id,
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
