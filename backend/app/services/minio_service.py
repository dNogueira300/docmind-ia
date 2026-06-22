"""Servicio de almacenamiento de archivos en MinIO."""
import io
import logging
from datetime import timedelta
from uuid import UUID

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger("docmind")


def _get_client() -> Minio:
    """Crea y retorna un cliente MinIO configurado (operaciones internas)."""
    return Minio(
        endpoint=settings.minio_host,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _get_public_client() -> Minio:
    """Cliente para firmar URLs accesibles desde el browser.

    `secure=False` fijo: el cliente solo firma (no conecta), y el esquema final
    (http/https) se ajusta sobre la URL en get_presigned_url según
    minio_public_secure. El esquema no forma parte de la firma SigV4.
    """
    return Minio(
        endpoint=settings.minio_public_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
        region="us-east-1",  # evita GetBucketLocation al endpoint público
    )


def ensure_bucket_exists() -> None:
    """Crea el bucket docmind-docs si no existe."""
    client = _get_client()
    bucket = settings.minio_bucket
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_file(
    file_data: bytes,
    filename: str,
    content_type: str,
    organization_id: UUID,
    document_id: UUID,
) -> str:
    """
    Sube un archivo a MinIO y retorna el stored_path.

    Ruta: {organization_id}/{year}/{month}/{document_id}_{filename}
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    stored_path = (
        f"{organization_id}/{now.year}/{now.month:02d}/{document_id}_{filename}"
    )

    client = _get_client()
    client.put_object(
        bucket_name=settings.minio_bucket,
        object_name=stored_path,
        data=io.BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )
    return stored_path


def upload_digitalized_docx(
    docx_bytes: bytes,
    original_stored_path: str,
) -> str:
    """
    Sube el .docx digitalizado junto al original.

    Toma el `stored_path` del original y le agrega el sufijo `.digitalized.docx`,
    manteniendo la misma jerarquía de carpetas (org_id/year/month/).
    """
    digitalized_path = f"{original_stored_path}.digitalized.docx"

    client = _get_client()
    client.put_object(
        bucket_name=settings.minio_bucket,
        object_name=digitalized_path,
        data=io.BytesIO(docx_bytes),
        length=len(docx_bytes),
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    return digitalized_path


def get_presigned_url(
    stored_path: str,
    expires_seconds: int = 3600,
    response_filename: str | None = None,
) -> str:
    """
    Genera URL firmada accesible desde el browser.

    Firma con el cliente público (endpoint resoluble por el navegador). La región
    fija evita el GetBucketLocation que fallaría contra el endpoint público.

    Si `response_filename` se pasa, fuerza un nombre amigable al descargar
    (Content-Disposition: attachment; filename=...).
    """
    client = _get_public_client()
    response_headers: dict | None = None
    if response_filename:
        response_headers = {
            "response-content-disposition": (
                f'attachment; filename="{response_filename}"'
            )
        }
    url = client.presigned_get_object(
        bucket_name=settings.minio_bucket,
        object_name=stored_path,
        expires=timedelta(seconds=expires_seconds),
        response_headers=response_headers,
    )
    # El esquema no se firma en SigV4 → seguro reescribirlo tras firmar.
    # MINIO_PUBLIC_SECURE no es fiable (en Railway está en false), así que el
    # esquema se decide por el host: localhost (dev) va por HTTP; cualquier otro
    # endpoint (dominio público de Railway) se sirve por HTTPS.
    public_host = settings.minio_public_endpoint
    is_local = public_host.startswith(("localhost", "127.0.0.1"))
    if not is_local:
        url = url.replace("http://", "https://", 1)
    logger.info("Presigned URL generada: %s", url)
    return url


def get_file_bytes(stored_path: str) -> bytes:
    """Descarga un archivo de MinIO y retorna su contenido como bytes."""
    client = _get_client()
    response = client.get_object(settings.minio_bucket, stored_path)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_file(stored_path: str) -> None:
    """Elimina un archivo de MinIO."""
    client = _get_client()
    try:
        client.remove_object(settings.minio_bucket, stored_path)
    except S3Error:
        pass  # Si no existe, no hay nada que eliminar
