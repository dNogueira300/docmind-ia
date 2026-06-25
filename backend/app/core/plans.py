"""Definición de planes SaaS, sus límites y features.

La fuente de verdad del plan de una organización es la columna `organizations.plan`
(+ `plan_expires_at`). Estos límites se definen en código para poder ajustarlos sin
migraciones. El enforcement vive en `app/services/plan_service.py` y se aplica en el
backend (nunca solo en el frontend).
"""
import enum


class Plan(str, enum.Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


# Features que se pueden activar/desactivar por plan.
# Nota: la DETECCIÓN de alertas de vencimiento es por código (regex) y está
# disponible en TODOS los planes; solo la descripción enriquecida con IA depende
# del plan (se controla con "ai_summary"). Por eso "alerts" no está aquí.
FEATURES = (
    "ai_classification",   # auto-clasificación con Gemini en el pipeline
    "ai_summary",          # resumen automático del documento (y descripción IA de alertas)
    "ai_suggestions",      # sugerencias de categoría
    "chatbot",             # chatbot documental y global
    "semantic_search",     # re-ranking semántico de búsqueda con IA
)

# Límites y features por plan.
PLAN_LIMITS: dict[Plan, dict] = {
    Plan.free: {
        "label": "Gratuito",
        "max_users": 5,
        "max_storage_mb": 200,
        "ai_credits_per_month": 0,
        "features": {f: False for f in FEATURES},
    },
    Plan.pro: {
        "label": "Pro",
        "max_users": 25,
        "max_storage_mb": 5_120,        # 5 GB
        "ai_credits_per_month": 1_000,
        "features": {f: True for f in FEATURES},
    },
    Plan.enterprise: {
        "label": "Enterprise",
        "max_users": 1_000,
        "max_storage_mb": 102_400,      # 100 GB
        "ai_credits_per_month": 100_000,
        "features": {f: True for f in FEATURES},
    },
}


def normalize_plan(value) -> Plan:
    """Convierte un string/enum a Plan; cae a free si es desconocido."""
    if isinstance(value, Plan):
        return value
    try:
        return Plan(str(value))
    except ValueError:
        return Plan.free


def plan_limits(plan) -> dict:
    return PLAN_LIMITS[normalize_plan(plan)]


def plan_feature(plan, feature: str) -> bool:
    return bool(plan_limits(plan)["features"].get(feature, False))
