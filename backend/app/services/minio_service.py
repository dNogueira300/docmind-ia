"""Servicio de almacenamiento de archivos en MinIO."""
import io
from datetime import timedelta
from uuid import UUID

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


def _get_client() -> Minio:
    """Crea y retorna un cliente MinIO configurado."""
    return Minio(
        endpoint=settings.minio_host,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
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
    from datetime import datetime

    now = datetime.utcnow()
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


def get_presigned_url(stored_path: str, expires_seconds: int = 3600) -> str:
    """Genera una URL firmada temporal para acceder al archivo."""
    client = _get_client()
    return client.presigned_get_object(
        bucket_name=settings.minio_bucket,
        object_name=stored_path,
        expires=timedelta(seconds=expires_seconds),
    )


def delete_file(stored_path: str) -> None:
    """Elimina un archivo de MinIO."""
    client = _get_client()
    try:
        client.remove_object(settings.minio_bucket, stored_path)
    except S3Error:
        pass  # Si no existe, no hay nada que eliminar
