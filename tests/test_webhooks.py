from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Participant, ParticipantResponse


def test_incoming_webhook_stores_response() -> None:
    with TestClient(app) as client:
        start = client.post(
            "/webhooks/twilio/incoming",
            data={
                "From": "whatsapp:+5511977776666",
                "To": "whatsapp:+14155238886",
                "Body": "INICIAR",
                "MessageSid": "SM-START",
                "NumMedia": "0",
            },
        )
        response = client.post(
            "/webhooks/twilio/incoming",
            data={
                "From": "whatsapp:+5511977776666",
                "To": "whatsapp:+14155238886",
                "Body": "Minha resposta",
                "MessageSid": "SM-RESPONSE",
                "NumMedia": "1",
                "MediaUrl0": "https://example.test/media.jpg",
            },
        )
    assert start.status_code == 200
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    with SessionLocal() as db:
        participant = db.scalar(
            select(Participant).where(Participant.phone == "+5511977776666")
        )
        assert participant is not None
        stored = db.scalar(
            select(ParticipantResponse).where(
                ParticipantResponse.participant_id == participant.id
            )
        )
        assert stored is not None
        assert stored.media_url == "https://example.test/media.jpg"
