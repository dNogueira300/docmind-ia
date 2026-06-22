"""Configuración global del proyecto leída desde variables de entorno."""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    access_token_expire_minutes: int = 480

    # MinIO
    minio_endpoint: str
    minio_endpoint_local: Optional[str] = None
    minio_public_endpoint: str = "localhost:9000"  # hostname accesible desde el browser
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "docmind-docs"
    minio_secure: bool = False
    # TLS para el endpoint público usado al firmar URLs accesibles desde el browser.
    # En Railway el bucket suele exponerse vía HTTPS → poner True; en local, False.
    minio_public_secure: bool = False

    # CORS
    allowed_origins: list[str] = ["*"]

    # Entorno
    environment: str = "development"
    running_in_docker: bool = False  # ← inyectada por docker-compose

    # Super admin bootstrap (creado por main.py::_ensure_super_admin())
    super_admin_email: str = "superadmin@docmind.local"
    super_admin_password: Optional[str] = None  # REQUERIDO en producción

    # Google Gemini API
    gemini_api_key: Optional[str] = None

    # NLP / clasificación zero-shot.
    # Override explícito del modelo. Si es None, nlp_service elige por entorno:
    # producción → modelo ligero (menos RAM); resto → modelo pesado (más preciso).
    nlp_model: Optional[str] = None

    @property
    def db_url(self) -> str:
        """Usa URL local solo cuando NO estamos en Docker."""
        if self.running_in_docker:
            return self.database_url
        return self.database_url_local or self.database_url

    @property
    def minio_host(self) -> str:
        """Usa endpoint local solo cuando NO estamos en Docker."""
        if self.running_in_docker:
            return self.minio_endpoint
        return self.minio_endpoint_local or self.minio_endpoint


settings = Settings()