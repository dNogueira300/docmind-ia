"""Precios de los planes: lectura pública (landing) y edición por super_admin."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_super_admin
from app.core.plans import Plan, PLAN_LIMITS, normalize_plan
from app.models.user import User
from app.models.plan_pricing import PlanPricing
from app.schemas.pricing import PlanPricingItem, PlanPricingUpdate

router = APIRouter(prefix="/pricing", tags=["Precios"])

SuperAdmin = Annotated[User, Depends(require_super_admin)]

# Orden en que se muestran los planes en la landing.
_PLAN_ORDER = [Plan.free, Plan.pro, Plan.enterprise]


def _to_item(pricing: PlanPricing) -> PlanPricingItem:
    plan = normalize_plan(pricing.plan)
    limits = PLAN_LIMITS[plan]
    return PlanPricingItem(
        plan=plan.value,
        label=limits["label"],
        price=float(pricing.price),
        currency=pricing.currency,
        period=pricing.period,
        tagline=pricing.tagline,
        highlight=pricing.highlight,
        custom_quote=pricing.custom_quote,
        limits={
            "max_users": limits["max_users"],
            "max_storage_mb": limits["max_storage_mb"],
            "ai_credits_per_month": limits["ai_credits_per_month"],
        },
        features=limits["features"],
    )


@router.get(
    "",
    response_model=list[PlanPricingItem],
    summary="Precios públicos de los planes (sin autenticación)",
)
async def get_pricing(db: Session = Depends(get_db)) -> list[PlanPricingItem]:
    """Devuelve los planes con su precio editable + límites y features (para la landing)."""
    rows = {p.plan: p for p in db.query(PlanPricing).all()}
    items: list[PlanPricingItem] = []
    for plan in _PLAN_ORDER:
        pricing = rows.get(plan.value)
        if pricing is None:
            # Fallback si la fila no existe aún: precio 0.
            pricing = PlanPricing(plan=plan.value, price=0, currency="S/", period="/mes")
        items.append(_to_item(pricing))
    return items


@router.put(
    "/{plan}",
    response_model=PlanPricingItem,
    summary="Editar el precio de un plan (super_admin)",
)
async def update_pricing(
    plan: str,
    data: PlanPricingUpdate,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> PlanPricingItem:
    plan_norm = normalize_plan(plan)
    pricing = db.query(PlanPricing).filter(PlanPricing.plan == plan_norm.value).first()
    if pricing is None:
        pricing = PlanPricing(plan=plan_norm.value)
        db.add(pricing)

    if data.price is not None:
        pricing.price = data.price
    if data.currency is not None:
        pricing.currency = data.currency
    if data.period is not None:
        pricing.period = data.period
    if data.tagline is not None:
        pricing.tagline = data.tagline
    if data.highlight is not None:
        pricing.highlight = data.highlight
    if data.custom_quote is not None:
        pricing.custom_quote = data.custom_quote

    db.commit()
    db.refresh(pricing)
    return _to_item(pricing)
