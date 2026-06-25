"""Punto de entrada de la aplicación FastAPI — DocMind IA."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
from app.api import auth, users, categories, documents, audit_log, organizations, alerts, approvals, risk_rules, chat, pricing

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

    # Asegurar que existe el super admin global
    try:
        _ensure_super_admin()
    except Exception as e:
        logger.warning("No se pudo asegurar el super admin: %s", e)

    yield

    logger.info("Apagando DocMind IA...")


def _ensure_super_admin() -> None:
    """
    Garantiza que exista un usuario super_admin global al arrancar.

    Si no hay ninguno en BD, crea uno con:
      - email:    settings.super_admin_email     (default: superadmin@docmind.local)
      - password: settings.super_admin_password  (REQUERIDO en producción)

    En desarrollo, si no se setea la contraseña, usa 'ChangeMe123!' y muestra
    un warning grande. NUNCA hardcodea contraseñas en producción.
    """
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    db = SessionLocal()
    try:
        exists = db.query(User).filter(User.role == UserRole.super_admin).first()
        if exists:
            logger.info("Super admin global ya existe (id=%s)", exists.id)
            return

        email = settings.super_admin_email
        password = settings.super_admin_password

        if not password:
            if settings.environment == "production":
                logger.error(
                    "SUPER_ADMIN_PASSWORD no definido en producción. "
                    "No se crea el super admin — define la variable y reinicia."
                )
                return
            password = "ChangeMe123!"
            logger.warning(
                "⚠️  Creando super admin con contraseña DE DESARROLLO "
                "'ChangeMe123!' — cámbiala inmediatamente o define "
                "SUPER_ADMIN_PASSWORD en .env"
            )

        super_admin = User(
            organization_id=None,
            name="Super Admin",
            email=email,
            password_hash=hash_password(password),
            role=UserRole.super_admin,
            active=True,
        )
        db.add(super_admin)
        db.commit()
        logger.info("Super admin global creado: %s", email)
    finally:
        db.close()


# ── Aplicación ────────────────────────────────────────────────────────────────
_is_prod = settings.environment == "production"

app = FastAPI(
    title="DocMind IA",
    description=(
        "Sistema de Gestión Documental Inteligente con IA — UNAP 2026\n\n"
        "Equipo: Error 404 | Backend: FastAPI + PostgreSQL + MinIO"
    ),
    version="0.2.0",
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
    lifespan=lifespan,
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Necesario para que JS pueda leer headers personalizados si los retornamos
    expose_headers=["X-Active-Tenant"],
)


# ── Middleware de seguridad — headers HTTP ────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


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
app.include_router(organizations.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(categories.router, prefix=PREFIX)
app.include_router(documents.router, prefix=PREFIX)
app.include_router(audit_log.router, prefix=PREFIX)
app.include_router(alerts.router, prefix=PREFIX)
app.include_router(approvals.router, prefix=PREFIX)
app.include_router(risk_rules.router, prefix=PREFIX)
app.include_router(chat.router, prefix=PREFIX)
app.include_router(pricing.router, prefix=PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Sistema"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "DocMind IA Backend",
        "version": "0.2.0",
        "environment": settings.environment,
    }
