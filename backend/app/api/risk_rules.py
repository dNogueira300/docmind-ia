"""CRUD de reglas de riesgo documental."""
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role, get_active_organization_id
from app.models.user import User
from app.models.risk_rule import RiskRule
from app.schemas.risk_rule import RiskRuleCreate, RiskRuleUpdate, RiskRuleResponse

router = APIRouter(prefix="/risk-rules", tags=["Riesgo"])

AdminOnly = Annotated[User, Depends(require_role("admin"))]


@router.get("/", response_model=list[RiskRuleResponse], summary="Listar reglas de riesgo")
async def list_risk_rules(
    current_user: AdminOnly,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> list[RiskRule]:
    return (
        db.query(RiskRule)
        .filter(RiskRule.organization_id == organization_id)
        .order_by(RiskRule.created_at.desc())
        .all()
    )


@router.post("/", response_model=RiskRuleResponse, status_code=201, summary="Crear regla de riesgo")
async def create_risk_rule(
    data: RiskRuleCreate,
    current_user: AdminOnly,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> RiskRule:
    rule = RiskRule(
        organization_id=organization_id,
        name=data.name,
        description=data.description,
        category_ids=data.category_ids,
        keywords=data.keywords,
        min_file_size_kb=data.min_file_size_kb,
        risk_level=data.risk_level,
        active=data.active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=RiskRuleResponse, summary="Editar regla de riesgo")
async def update_risk_rule(
    rule_id: UUID,
    data: RiskRuleUpdate,
    current_user: AdminOnly,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> RiskRule:
    rule = (
        db.query(RiskRule)
        .filter(RiskRule.id == rule_id, RiskRule.organization_id == organization_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", summary="Eliminar regla de riesgo")
async def delete_risk_rule(
    rule_id: UUID,
    current_user: AdminOnly,
    organization_id: UUID = Depends(get_active_organization_id),
    db: Session = Depends(get_db),
) -> dict:
    rule = (
        db.query(RiskRule)
        .filter(RiskRule.id == rule_id, RiskRule.organization_id == organization_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    db.delete(rule)
    db.commit()
    return {"detail": f"Regla '{rule.name}' eliminada"}
