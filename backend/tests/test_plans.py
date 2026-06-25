"""Tests de monetización: planes, límites y códigos de activación."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

ORG_ID = "00000000-0000-0000-0000-000000000001"


def test_get_plan_overview(client: TestClient, admin_token: str):
    """El endpoint de plan devuelve plan, límites, features y uso."""
    resp = client.get(
        "/api/v1/organizations/plan",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "plan" in body and "features" in body and "limits" in body and "usage" in body


def test_activar_codigo_voltea_el_plan(client: TestClient, admin_token: str, db):
    """Canjear un código de activación cambia el plan de la organización."""
    from app.models.activation_code import ActivationCode
    from app.models.organization import Organization

    org = db.query(Organization).filter(Organization.id == ORG_ID).first()
    original_plan = org.plan
    original_expires = org.plan_expires_at

    # Crear un código pro directamente en BD
    db.query(ActivationCode).filter(ActivationCode.code == "DOCMIND-TEST-CODE").delete()
    db.commit()
    code = ActivationCode(code="DOCMIND-TEST-CODE", plan="pro", duration_days=30)
    db.add(code)
    db.commit()

    try:
        resp = client.post(
            "/api/v1/organizations/activate",
            json={"code": "DOCMIND-TEST-CODE"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["plan"] == "pro"

        db.refresh(org)
        assert org.plan == "pro"
        assert org.plan_expires_at is not None

        # El código quedó marcado como usado
        db.refresh(code)
        assert code.used is True
    finally:
        # Restaurar estado original para no afectar otros tests
        org.plan = original_plan
        org.plan_expires_at = original_expires
        db.query(ActivationCode).filter(ActivationCode.code == "DOCMIND-TEST-CODE").delete()
        db.commit()


def test_codigo_invalido_404(client: TestClient, admin_token: str):
    resp = client.post(
        "/api/v1/organizations/activate",
        json={"code": "DOCMIND-NOPE-NOPE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
