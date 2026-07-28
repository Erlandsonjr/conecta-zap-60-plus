from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class MessagingResult:
    success: bool
    message_id: str | None
    status: str
    error: str | None = None


class MessagingProvider(ABC):
    name: str

    @abstractmethod
    def send_text(self, to: str, body: str) -> MessagingResult:
        raise NotImplementedError

    @abstractmethod
    def send_media(self, to: str, body: str, media_url: str) -> MessagingResult:
        raise NotImplementedError
