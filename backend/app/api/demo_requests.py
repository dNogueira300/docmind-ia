"""Solicitudes de demo/acceso: alta pública (landing) y gestión por super_admin.

El "envío de correo" NO está implementado: al responder se guarda el mensaje y se
genera (opcionalmente) un código de activación para entrega manual.
"""
import secrets
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_super_admin
from app.core.limiter import limiter
from app.core.plans import Plan, normalize_plan
from app.models.user import User
from app.models.demo_request import DemoRequest
from app.models.activation_code import ActivationCode
from app.schemas.demo_request import (
    DemoRequestCreate, DemoRequestResponse, DemoRequestRespond,
)

router = APIRouter(prefix="/demo-requests", tags=["Solicitudes de demo"])

SuperAdmin = Annotated[User, Depends(require_super_admin)]


def _generate_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    part = lambda: "".join(secrets.choice(alphabet) for _ in range(4))
    return f"DOCMIND-{part()}-{part()}"


@router.post(
    "",
    response_model=DemoRequestResponse,
    status_code=201,
    summary="Solicitar acceso/demo (público)",
)
@limiter.limit("5/minute")
async def create_demo_request(
    request: Request,
    data: DemoRequestCreate,
    db: Session = Depends(get_db),
) -> DemoRequest:
    """Registra una solicitud de acceso desde la landing (sin autenticación)."""
    req = DemoRequest(
        name=data.name,
        email=str(data.email),
        organization_name=(data.organization_name or "").strip() or None,
        plan=normalize_plan(data.plan).value,
        message=(data.message or "").strip() or None,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get(
    "",
    response_model=list[DemoRequestResponse],
    summary="Listar solicitudes de demo (super_admin)",
)
async def list_demo_requests(
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
    status_filter: str = "",
) -> list[DemoRequest]:
    q = db.query(DemoRequest)
    if status_filter:
        q = q.filter(DemoRequest.status == status_filter)
    return q.order_by(DemoRequest.created_at.desc()).limit(200).all()


@router.post(
    "/{request_id}/respond",
    response_model=DemoRequestResponse,
    summary="Responder solicitud (simula el correo) y crear acceso (super_admin)",
)
async def respond_demo_request(
    request_id: UUID,
    data: DemoRequestRespond,
    current_user: SuperAdmin,
    db: Session = Depends(get_db),
) -> DemoRequest:
    """
    Marca la solicitud como respondida con un mensaje. Si `generate_code` y el plan
    es de pago, genera un código de activación y lo adjunta. NO envía correo todavía.
    """
    req = db.query(DemoRequest).filter(DemoRequest.id == request_id).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    plan = normalize_plan(data.plan or req.plan)

    code_str = None
    if data.generate_code and plan != Plan.free:
        code_str = _generate_code()
        while db.query(ActivationCode).filter(ActivationCode.code == code_str).first():
            code_str = _generate_code()
        db.add(ActivationCode(
            code=code_str, plan=plan.value, duration_days=data.duration_days
        ))
        req.activation_code = code_str

    req.response_message = data.message
    req.status = "responded"
    req.responded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    req.responded_by = current_user.id
    db.commit()
    db.refresh(req)
    return req
