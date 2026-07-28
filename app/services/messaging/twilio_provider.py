import logging

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.config import Settings
from app.services.messaging.base import MessagingProvider, MessagingResult

logger = logging.getLogger(__name__)


class TwilioWhatsAppProvider(MessagingProvider):
    name = "twilio"

    def __init__(self, settings: Settings) -> None:
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            raise ValueError("Twilio credentials are not configured")
        self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self.from_number = settings.twilio_whatsapp_from
        self.status_callback = (
            f"{settings.base_url.rstrip('/')}/webhooks/twilio/status"
        )

    @staticmethod
    def _recipient(to: str) -> str:
        return to if to.startswith("whatsapp:") else f"whatsapp:{to}"

    def send_text(self, to: str, body: str) -> MessagingResult:
        return self._send(to=to, body=body)

    def send_media(self, to: str, body: str, media_url: str) -> MessagingResult:
        return self._send(to=to, body=body, media_url=media_url)

    def _send(self, to: str, body: str, media_url: str | None = None) -> MessagingResult:
        try:
            payload: dict[str, object] = {
                "from_": self.from_number,
                "to": self._recipient(to),
                "body": body,
                "status_callback": self.status_callback,
            }
            if media_url:
                payload["media_url"] = [media_url]
            message = self.client.messages.create(**payload)
            return MessagingResult(True, message.sid, message.status or "queued")
        except (TwilioRestException, ValueError) as exc:
            logger.error("Twilio delivery failed: %s", exc)
            return MessagingResult(False, None, "failed", str(exc))


def create_provider(settings: Settings) -> MessagingProvider:
    if settings.messaging_provider == "twilio":
        return TwilioWhatsAppProvider(settings)
    from app.services.messaging.mock_provider import MockWhatsAppProvider

    return MockWhatsAppProvider()
