"""Schemas para la página pública de precios."""
from typing import Optional

from pydantic import BaseModel, field_validator


class PlanPricingItem(BaseModel):
    """Un plan tal como se muestra en la landing (precio editable + límites/features)."""
    plan: str
    label: str
    price: float
    currency: str
    period: str
    tagline: Optional[str] = None
    highlight: bool = False
    custom_quote: bool = False
    limits: dict
    features: dict


class PlanPricingUpdate(BaseModel):
    """Campos editables del precio de un plan (super_admin)."""
    price: Optional[float] = None
    currency: Optional[str] = None
    period: Optional[str] = None
    tagline: Optional[str] = None
    highlight: Optional[bool] = None
    custom_quote: Optional[bool] = None

    @field_validator("price")
    @classmethod
    def _price_ok(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("El precio no puede ser negativo")
        return v
