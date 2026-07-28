import re
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Delivery, Feedback, Participant, ParticipantResponse, Pill, local_now
from app.services.messaging.base import MessagingProvider, MessagingResult

WELCOME_MESSAGE = (
    "Olá! Você confirmou sua participação no Conecta-Zap 60+. "
    "Serão 10 mensagens curtas sobre segurança e autonomia digital. "
    "Responda AJUDA quando precisar ou SAIR para interromper."
)
EXIT_MESSAGE = "Sua participação foi pausada. Você não receberá novos envios. Obrigado por participar."
HELP_MESSAGE = (
    "Estamos aqui para ajudar. Leia a mensagem com calma e não compartilhe senhas ou códigos. "
    "Se ainda tiver dúvida, procure uma pessoa de confiança. Envie SAIR para interromper os envios."
)
COMPLETION_MESSAGE = (
    "Parabéns! Você concluiu as 10 pílulas do Conecta-Zap 60+. "
    "Para deixar seu feedback, responda no formato: "
    "FEEDBACK 5 | SIM | conteúdo mais útil | SIM | comentário opcional"
)


class AutomationService:
    def __init__(
        self,
        db: Session,
        provider: MessagingProvider,
        settings: Settings,
    ) -> None:
        self.db = db
        self.provider = provider
        self.settings = settings

    def process_incoming(
        self,
        phone: str,
        body: str,
        media_url: str | None = None,
        name: str = "Participante WhatsApp",
    ) -> tuple[Participant, str]:
        normalized_phone = self.normalize_phone(phone)
        participant = self.db.scalar(
            select(Participant).where(Participant.phone == normalized_phone)
        )
        if participant is None:
            participant = Participant(name=name, phone=normalized_phone, mode="demo")
            self.db.add(participant)
            self.db.flush()

        command = self.normalize_command(body)
        if command == "INICIAR":
            participant.consent_given = True
            participant.active = True
            participant.current_pill = 1
            participant.started_at = local_now()
            participant.completed_at = None
            participant.next_delivery_at = self.next_delivery_time(participant.mode)
            self._send_event(participant, WELCOME_MESSAGE)
            reply = WELCOME_MESSAGE
        elif command == "SAIR":
            participant.active = False
            participant.next_delivery_at = None
            self._send_event(participant, EXIT_MESSAGE)
            reply = EXIT_MESSAGE
        elif command == "AJUDA":
            self._send_event(participant, HELP_MESSAGE)
            reply = HELP_MESSAGE
        else:
            last_pill_id = self.db.scalar(
                select(Delivery.pill_id)
                .where(
                    Delivery.participant_id == participant.id,
                    Delivery.pill_id.is_not(None),
                    Delivery.status != "failed",
                )
                .order_by(Delivery.sent_at.desc(), Delivery.id.desc())
                .limit(1)
            )
            self.db.add(
                ParticipantResponse(
                    participant_id=participant.id,
                    pill_id=last_pill_id,
                    message_body=body.strip(),
                    media_url=media_url,
                )
            )
            self._try_store_feedback(participant, body)
            reply = "Mensagem recebida. Obrigado pela sua resposta!"

        self.db.commit()
        return participant, reply

    def send_next_pill(self, participant: Participant) -> Delivery:
        if not participant.consent_given:
            raise ValueError("Participant has not provided consent")
        if not participant.active:
            raise ValueError("Participant is not active")

        pills = list(
            self.db.scalars(
                select(Pill)
                .where(Pill.active.is_(True), Pill.order_number >= participant.current_pill)
                .order_by(Pill.order_number)
            )
        )
        for pill in pills:
            already_sent = self.db.scalar(
                select(Delivery.id).where(
                    Delivery.participant_id == participant.id,
                    Delivery.pill_id == pill.id,
                    Delivery.status != "failed",
                )
            )
            if already_sent is None:
                delivery = self.send_pill(participant, pill, force=False)
                if delivery.status == "failed":
                    participant.next_delivery_at = self.next_delivery_time(participant.mode)
                    self.db.commit()
                    raise ValueError(
                        delivery.error_message or "Message provider failed to send the pill"
                    )
                participant.current_pill = pill.order_number + 1
                if pill.order_number >= 10:
                    self._complete_track(participant)
                else:
                    participant.next_delivery_at = self.next_delivery_time(participant.mode)
                self.db.commit()
                return delivery
            participant.current_pill = max(participant.current_pill, pill.order_number + 1)

        self._complete_track(participant)
        self.db.commit()
        raise ValueError("All pills have already been sent")

    def send_pill(self, participant: Participant, pill: Pill, force: bool = False) -> Delivery:
        if not force:
            existing = self.db.scalar(
                select(Delivery.id).where(
                    Delivery.participant_id == participant.id,
                    Delivery.pill_id == pill.id,
                    Delivery.status != "failed",
                )
            )
            if existing is not None:
                raise ValueError("This pill has already been sent")

        body = (
            f"Pílula {pill.order_number}/10 — {pill.title}\n\n"
            f"{pill.message}\n\nAgora é sua vez: {pill.call_to_action}"
        )
        media_url = (
            f"{self.settings.base_url.rstrip('/')}/static/images/{pill.image_filename}"
        )
        result = self.provider.send_media(participant.phone, body, media_url)
        delivery = self._delivery_from_result(participant, result, pill.id)
        self.db.add(delivery)
        self.db.flush()
        return delivery

    def run_demo(self, participant: Participant) -> int:
        if participant.mode != "demo":
            raise ValueError("Accelerated execution is only available in demo mode")
        sent = 0
        while participant.active and participant.current_pill <= 10:
            self.send_next_pill(participant)
            sent += 1
        return sent

    def reset_participant(self, participant: Participant) -> None:
        participant.active = False
        participant.consent_given = False
        participant.current_pill = 1
        participant.started_at = None
        participant.completed_at = None
        participant.next_delivery_at = None
        for delivery in list(participant.deliveries):
            self.db.delete(delivery)
        for response in list(participant.responses):
            self.db.delete(response)
        for feedback in list(participant.feedbacks):
            self.db.delete(feedback)
        self.db.commit()

    def resume_participant(self, participant: Participant) -> None:
        if not participant.consent_given:
            raise ValueError("Consent is required before resuming")
        if participant.completed_at:
            raise ValueError("Completed participants cannot be resumed without resetting")
        participant.active = True
        participant.next_delivery_at = self.next_delivery_time(participant.mode)
        self.db.commit()

    def next_delivery_time(self, mode: str) -> datetime:
        now = local_now()
        if mode == "demo":
            return now + timedelta(minutes=self.settings.demo_interval_minutes)
        scheduled = now.replace(
            hour=self.settings.real_delivery_hour, minute=0, second=0, microsecond=0
        )
        if scheduled <= now:
            scheduled += timedelta(days=1)
        return scheduled

    @staticmethod
    def normalize_command(body: str) -> str:
        return re.sub(r"\s+", " ", body.strip()).upper()

    @staticmethod
    def normalize_phone(phone: str) -> str:
        raw = phone.replace("whatsapp:", "").strip()
        digits = re.sub(r"\D", "", raw)
        return f"+{digits}"

    def _send_event(self, participant: Participant, body: str) -> Delivery:
        result = self.provider.send_text(participant.phone, body)
        delivery = self._delivery_from_result(participant, result, None)
        self.db.add(delivery)
        self.db.flush()
        return delivery

    def _delivery_from_result(
        self,
        participant: Participant,
        result: MessagingResult,
        pill_id: int | None,
    ) -> Delivery:
        timestamp = local_now()
        return Delivery(
            participant_id=participant.id,
            pill_id=pill_id,
            provider=self.provider.name,
            provider_message_id=result.message_id,
            status=result.status,
            error_message=result.error,
            sent_at=timestamp if result.success else None,
            delivered_at=timestamp if result.status == "delivered" else None,
        )

    def _complete_track(self, participant: Participant) -> None:
        if participant.completed_at is None:
            participant.completed_at = local_now()
            participant.active = False
            participant.next_delivery_at = None
            self._send_event(participant, COMPLETION_MESSAGE)

    def _try_store_feedback(self, participant: Participant, body: str) -> None:
        if not participant.completed_at or not body.strip().upper().startswith("FEEDBACK"):
            return
        parts = [part.strip() for part in body[8:].strip().split("|")]
        if len(parts) < 4:
            return
        try:
            score = int(parts[0])
        except ValueError:
            return
        if score not in range(1, 6):
            return
        yes = {"SIM", "S", "YES"}
        self.db.add(
            Feedback(
                participant_id=participant.id,
                easy_to_understand=score,
                learned_something=parts[1].upper() in yes,
                most_useful_content=parts[2][:500],
                would_recommend=parts[3].upper() in yes,
                additional_comment=parts[4][:1000] if len(parts) > 4 else None,
            )
        )


def dashboard_counts(db: Session) -> dict[str, int | float]:
    total = db.scalar(select(func.count(Participant.id))) or 0
    active = db.scalar(
        select(func.count(Participant.id)).where(Participant.active.is_(True))
    ) or 0
    completed = db.scalar(
        select(func.count(Participant.id)).where(Participant.completed_at.is_not(None))
    ) or 0
    pills_sent = db.scalar(
        select(func.count(Delivery.id)).where(
            Delivery.pill_id.is_not(None), Delivery.status != "failed"
        )
    ) or 0
    responses = db.scalar(select(func.count(ParticipantResponse.id))) or 0
    feedbacks = db.scalar(select(func.count(Feedback.id))) or 0
    completion_rate = round((completed / total) * 100, 1) if total else 0.0
    return {
        "total": total,
        "active": active,
        "completed": completed,
        "pills_sent": pills_sent,
        "responses": responses,
        "feedbacks": feedbacks,
        "completion_rate": completion_rate,
    }
