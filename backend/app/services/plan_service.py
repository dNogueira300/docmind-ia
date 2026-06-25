"""Lógica de planes SaaS: plan efectivo, features, créditos de IA y límites.

Todo el enforcement de monetización pasa por aquí. Los endpoints y el pipeline
consultan estas funciones; nunca confían en el frontend.
"""
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.plans import Plan, plan_limits, plan_feature, normalize_plan
from app.models.organization import Organization
from app.models.user import User
from app.models.document import Document

logger = logging.getLogger("docmind")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def effective_plan(org: Organization) -> Plan:
    """Plan vigente de la organización. Si el plan de pago venció → free."""
    plan = normalize_plan(org.plan)
    if plan != Plan.free and org.plan_expires_at and org.plan_expires_at < _now():
        return Plan.free
    return plan


def has_feature(org: Organization, feature: str) -> bool:
    """True si el plan efectivo de la org habilita la feature dada."""
    return plan_feature(effective_plan(org), feature)


def get_org(db: Session, organization_id) -> Organization | None:
    return db.query(Organization).filter(Organization.id == organization_id).first()


# ── Límite de usuarios ────────────────────────────────────────────────────────

def user_count(db: Session, organization_id) -> int:
    return (
        db.query(func.count(User.id))
        .filter(User.organization_id == organization_id)
        .scalar()
        or 0
    )


def can_add_user(db: Session, org: Organization) -> bool:
    limit = plan_limits(effective_plan(org))["max_users"]
    return user_count(db, org.id) < limit


# ── Límite de almacenamiento ──────────────────────────────────────────────────

def storage_used_kb(db: Session, organization_id) -> int:
    return int(
        db.query(func.coalesce(func.sum(Document.file_size_kb), 0))
        .filter(Document.organization_id == organization_id)
        .scalar()
        or 0
    )


def can_store(db: Session, org: Organization, new_file_kb: int) -> bool:
    limit_kb = plan_limits(effective_plan(org))["max_storage_mb"] * 1024
    return storage_used_kb(db, org.id) + (new_file_kb or 0) <= limit_kb


# ── Créditos de IA (cuota mensual) ────────────────────────────────────────────

def _ensure_credit_window(org: Organization) -> None:
    """Reinicia el contador mensual si la ventana venció (reset perezoso)."""
    now = _now()
    if org.ai_credits_reset_at is None or org.ai_credits_reset_at < now:
        org.ai_credits_used = 0
        org.ai_credits_reset_at = now + timedelta(days=30)


def ai_credits_status(db: Session, org: Organization) -> dict:
    """Estado de créditos del periodo vigente (no consume)."""
    limit = plan_limits(effective_plan(org))["ai_credits_per_month"]
    used = org.ai_credits_used or 0
    # Si la ventana venció, a efectos de lectura se reporta como reiniciada.
    if org.ai_credits_reset_at is not None and org.ai_credits_reset_at < _now():
        used = 0
    return {
        "limit": limit,
        "used": used,
        "remaining": max(0, limit - used),
        "reset_at": org.ai_credits_reset_at,
    }


def consume_ai_credit(db: Session, org: Organization, n: int = 1) -> bool:
    """
    Intenta consumir n créditos de IA del periodo vigente.

    Returns True si había crédito suficiente (y lo descuenta), False si no.
    El caller debe saltarse la acción de IA cuando devuelve False.
    """
    limit = plan_limits(effective_plan(org))["ai_credits_per_month"]
    _ensure_credit_window(org)
    if org.ai_credits_used + n > limit:
        db.commit()  # persistir el posible reset de ventana
        logger.info(
            "Org %s sin créditos de IA (%s/%s)", org.id, org.ai_credits_used, limit
        )
        return False
    org.ai_credits_used += n
    db.commit()
    return True


# ── Resumen del plan para el frontend ─────────────────────────────────────────

def plan_overview(db: Session, org: Organization) -> dict:
    plan = effective_plan(org)
    limits = plan_limits(plan)
    credits = ai_credits_status(db, org)
    return {
        "plan": plan.value,
        "plan_label": limits["label"],
        "plan_expires_at": org.plan_expires_at,
        "features": limits["features"],
        "limits": {
            "max_users": limits["max_users"],
            "max_storage_mb": limits["max_storage_mb"],
            "ai_credits_per_month": limits["ai_credits_per_month"],
        },
        "usage": {
            "users": user_count(db, org.id),
            "storage_mb": round(storage_used_kb(db, org.id) / 1024, 2),
            "ai_credits_used": credits["used"],
            "ai_credits_remaining": credits["remaining"],
        },
    }
