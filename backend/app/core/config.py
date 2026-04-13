"""Configuración global del proyecto leída desde variables de entorno."""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# El .env vive en la raíz del proyecto (un nivel arriba de backend/)
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base de datos
    database_url: str
    database_url_local: Optional[str] = None

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 horas

    # MinIO
    minio_endpoint: str
    minio_endpoint_local: Optional[str] = None
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "docmind-docs"
    minio_secure: bool = False

    # Entorno
    environment: str = "development"

    @property
    def db_url(self) -> str:
        """Usa URL local si está disponible (desarrollo fuera de Docker)."""
        return self.database_url_local or self.database_url

    @property
    def minio_host(self) -> str:
        """Usa endpoint local si está disponible."""
        return self.minio_endpoint_local or self.minio_endpoint


settings = Settings()
