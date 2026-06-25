"""Tests de solicitudes de demo (landing pública + gestión super_admin)."""
from fastapi.testclient import TestClient


def test_crear_solicitud_demo_publica(client: TestClient, db):
    """Cualquiera (sin token) puede enviar una solicitud de demo."""
    from app.models.demo_request import DemoRequest

    db.query(DemoRequest).filter(DemoRequest.email == "demo_test@ejemplo.com").delete()
    db.commit()

    resp = client.post(
        "/api/v1/demo-requests",
        json={
            "name": "María Test",
            "email": "demo_test@ejemplo.com",
            "plan": "pro",
            "message": "Quiero una demo",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["plan"] == "pro"
    assert body["activation_code"] is None

    db.query(DemoRequest).filter(DemoRequest.email == "demo_test@ejemplo.com").delete()
    db.commit()


def test_responder_requiere_super_admin(client: TestClient, admin_token: str, db):
    """Un admin de empresa NO puede responder solicitudes (solo super_admin)."""
    from app.models.demo_request import DemoRequest
    import uuid

    req = DemoRequest(name="X", email="x@e.com", plan="pro", status="pending")
    db.add(req)
    db.commit()
    db.refresh(req)

    try:
        resp = client.post(
            f"/api/v1/demo-requests/{req.id}/respond",
            json={"message": "Hola", "generate_code": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 403
    finally:
        db.delete(req)
        db.commit()


def test_listar_solicitudes_requiere_super_admin(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/demo-requests",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403
