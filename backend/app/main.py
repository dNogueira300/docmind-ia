"""Punto de entrada de la aplicación FastAPI — DocMind IA."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth, users, categories, documents, audit_log

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("docmind")


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Tareas de inicio: verificar BD y crear bucket MinIO."""
    logger.info("Iniciando DocMind IA — entorno: %s", settings.environment)

    try:
        from app.core.database import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexión a PostgreSQL OK")
    except Exception as e:
        logger.error("Error conectando a PostgreSQL: %s", e)

    try:
        from app.services.minio_service import ensure_bucket_exists

        ensure_bucket_exists()
        logger.info("Bucket MinIO '%s' listo", settings.minio_bucket)
    except Exception as e:
        logger.warning("No se pudo verificar MinIO: %s", e)

    yield

    logger.info("Apagando DocMind IA...")


# ── Aplicación ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DocMind IA",
    description=(
        "Sistema de Gestión Documental Inteligente con IA — UNAP 2026\n\n"
        "Equipo: Error 404 | Backend: FastAPI + PostgreSQL + MinIO"
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware de logging de requests ─────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("%s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.info("→ %s", response.status_code)
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(categories.router, prefix=PREFIX)
app.include_router(documents.router, prefix=PREFIX)
app.include_router(audit_log.router, prefix=PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Sistema"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "DocMind IA Backend",
        "version": "0.2.0",
        "environment": settings.environment,
    }
