import logging
from uuid import uuid4

from app.services.messaging.base import MessagingProvider, MessagingResult

logger = logging.getLogger(__name__)


def mask_phone(phone: str) -> str:
    digits = phone.replace("whatsapp:", "")
    if len(digits) <= 6:
        return "***"
    return f"{digits[:3]}***{digits[-4:]}"


class MockWhatsAppProvider(MessagingProvider):
    name = "mock"

    def send_text(self, to: str, body: str) -> MessagingResult:
        message_id = f"MOCK-{uuid4().hex}"
        logger.info("Mock text sent to %s with id %s", mask_phone(to), message_id)
        return MessagingResult(True, message_id, "delivered")

    def send_media(self, to: str, body: str, media_url: str) -> MessagingResult:
        message_id = f"MOCK-{uuid4().hex}"
        logger.info("Mock media sent to %s with id %s", mask_phone(to), message_id)
        return MessagingResult(True, message_id, "delivered")
