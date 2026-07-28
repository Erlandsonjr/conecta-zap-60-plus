from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Participant


def test_health_route() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_participant_registration(admin_auth: tuple[str, str]) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/admin/participants",
            data={"name": "Maria da Silva", "phone": "(11) 99999-1234", "mode": "demo"},
            auth=admin_auth,
            follow_redirects=False,
        )
    assert response.status_code == 303
    with SessionLocal() as db:
        participant = db.scalar(
            select(Participant).where(Participant.name == "Maria da Silva")
        )
        assert participant is not None
        assert participant.phone == "+5511999991234"
        assert participant.mode == "demo"
        assert participant.consent_given is False


def test_admin_pages_require_auth_and_render(admin_auth: tuple[str, str]) -> None:
    with TestClient(app) as client:
        unauthorized = client.get("/admin")
        dashboard = client.get("/admin", auth=admin_auth)
        pills = client.get("/admin/pills", auth=admin_auth)
        participants = client.get("/admin/participants", auth=admin_auth)
    assert unauthorized.status_code == 401
    assert dashboard.status_code == 200
    assert "Visão geral do projeto" in dashboard.text
    assert pills.status_code == 200
    assert "As 10 pílulas" in pills.text
    assert participants.status_code == 200
