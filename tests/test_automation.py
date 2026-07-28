import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Delivery, Feedback, Participant, ParticipantResponse, Pill
from app.services.automation_service import AutomationService
from app.services.messaging.mock_provider import MockWhatsAppProvider


def make_service(db: Session) -> AutomationService:
    settings = Settings(
        database_url="sqlite:///./test_conecta_zap.db",
        messaging_provider="mock",
        scheduler_enabled=False,
    )
    return AutomationService(db, MockWhatsAppProvider(), settings)


def active_participant(db: Session) -> Participant:
    participant = Participant(
        name="João Teste",
        phone="+5511988887777",
        mode="demo",
        consent_given=True,
        active=True,
        current_pill=1,
    )
    db.add(participant)
    db.commit()
    return participant


def test_start_command(db_session: Session) -> None:
    service = make_service(db_session)
    participant, reply = service.process_incoming(
        "whatsapp:+5511912345678", "  iniciar "
    )
    assert participant.consent_given is True
    assert participant.active is True
    assert participant.current_pill == 1
    assert participant.started_at is not None
    assert participant.next_delivery_at is not None
    assert "confirmou sua participação" in reply
    assert len(participant.deliveries) == 1


def test_exit_command(db_session: Session) -> None:
    service = make_service(db_session)
    participant, _ = service.process_incoming("+5511912345678", "INICIAR")
    participant, reply = service.process_incoming("+5511912345678", "sair")
    assert participant.active is False
    assert participant.next_delivery_at is None
    assert "não receberá novos envios" in reply


def test_send_next_pill(db_session: Session) -> None:
    participant = active_participant(db_session)
    delivery = make_service(db_session).send_next_pill(participant)
    assert delivery.pill is not None
    assert delivery.pill.order_number == 1
    assert delivery.status == "delivered"
    assert participant.current_pill == 2


def test_prevents_duplicate_pill(db_session: Session) -> None:
    participant = active_participant(db_session)
    service = make_service(db_session)
    pill = db_session.scalar(select(Pill).where(Pill.order_number == 1))
    assert pill is not None
    service.send_pill(participant, pill)
    db_session.commit()
    with pytest.raises(ValueError, match="already been sent"):
        service.send_pill(participant, pill)
    count = db_session.scalar(
        select(func.count(Delivery.id)).where(
            Delivery.participant_id == participant.id,
            Delivery.pill_id == pill.id,
        )
    )
    assert count == 1


def test_completion_after_tenth_pill(db_session: Session) -> None:
    participant = active_participant(db_session)
    service = make_service(db_session)
    for _ in range(10):
        service.send_next_pill(participant)
    assert participant.completed_at is not None
    assert participant.active is False
    assert participant.current_pill == 11
    pill_deliveries = db_session.scalar(
        select(func.count(Delivery.id)).where(
            Delivery.participant_id == participant.id,
            Delivery.pill_id.is_not(None),
        )
    )
    system_deliveries = db_session.scalar(
        select(func.count(Delivery.id)).where(
            Delivery.participant_id == participant.id,
            Delivery.pill_id.is_(None),
        )
    )
    assert pill_deliveries == 10
    assert system_deliveries == 1


def test_stores_response_for_last_pill(db_session: Session) -> None:
    participant = active_participant(db_session)
    service = make_service(db_session)
    delivery = service.send_next_pill(participant)
    service.process_incoming(participant.phone, "CONSEGUI")
    response = db_session.scalar(
        select(ParticipantResponse).where(
            ParticipantResponse.participant_id == participant.id
        )
    )
    assert response is not None
    assert response.message_body == "CONSEGUI"
    assert response.pill_id == delivery.pill_id


def test_feedback_is_parsed_after_completion(db_session: Session) -> None:
    participant = active_participant(db_session)
    service = make_service(db_session)
    for _ in range(10):
        service.send_next_pill(participant)
    service.process_incoming(
        participant.phone,
        "FEEDBACK 5 | SIM | Pix com segurança | SIM | Muito bom",
    )
    feedback = db_session.scalar(
        select(Feedback).where(Feedback.participant_id == participant.id)
    )
    assert feedback is not None
    assert feedback.easy_to_understand == 5
    assert feedback.learned_something is True
    assert feedback.would_recommend is True


def test_mock_provider() -> None:
    provider = MockWhatsAppProvider()
    text_result = provider.send_text("+5511999999999", "Teste")
    media_result = provider.send_media(
        "+5511999999999",
        "Teste com imagem",
        "http://localhost:8000/static/images/infografico-01.png",
    )
    assert text_result.success is True
    assert text_result.status == "delivered"
    assert text_result.message_id is not None
    assert media_result.success is True
    assert media_result.status == "delivered"
