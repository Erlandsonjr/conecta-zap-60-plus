import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.config import Settings
from app.database import SessionLocal
from app.models import Participant
from app.services.automation_service import AutomationService
from app.services.messaging.twilio_provider import create_provider

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.scheduler = BackgroundScheduler(timezone=settings.app_timezone)

    def start(self) -> None:
        if self.scheduler.running:
            return
        self.scheduler.add_job(
            self.process_due_deliveries,
            trigger="interval",
            seconds=30,
            id="process_due_deliveries",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.start()
        logger.info("Delivery scheduler started")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def process_due_deliveries(self) -> None:
        with SessionLocal() as db:
            participants = list(
                db.scalars(
                    select(Participant).where(
                        Participant.active.is_(True),
                        Participant.consent_given.is_(True),
                        Participant.next_delivery_at.is_not(None),
                        Participant.next_delivery_at <= datetime.now(),
                    )
                )
            )
            provider = create_provider(self.settings)
            service = AutomationService(db, provider, self.settings)
            for participant in participants:
                try:
                    service.send_next_pill(participant)
                except ValueError as exc:
                    logger.warning(
                        "Scheduled delivery skipped for participant %s: %s",
                        participant.id,
                        exc,
                    )
                except Exception:
                    logger.exception(
                        "Unexpected scheduled delivery error for participant %s",
                        participant.id,
                    )
