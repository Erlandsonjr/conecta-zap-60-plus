from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def local_now() -> datetime:
    return datetime.now()


class ParticipantMode(str, Enum):
    DEMO = "demo"
    REAL = "real"


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    current_pill: Mapped[int] = mapped_column(Integer, default=1)
    mode: Mapped[str] = mapped_column(String(10), default=ParticipantMode.DEMO.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=local_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_delivery_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    deliveries: Mapped[list["Delivery"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )
    responses: Mapped[list["ParticipantResponse"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )

    @property
    def progress_count(self) -> int:
        return len(
            {
                delivery.pill_id
                for delivery in self.deliveries
                if delivery.pill_id is not None and delivery.status != "failed"
            }
        )

    @property
    def progress_percent(self) -> int:
        return min(self.progress_count * 10, 100)


class Pill(Base):
    __tablename__ = "pills"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    objective: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    call_to_action: Mapped[str] = mapped_column(Text)
    expected_answer: Mapped[str] = mapped_column(String(180))
    image_filename: Mapped[str] = mapped_column(String(180))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    deliveries: Mapped[list["Delivery"]] = relationship(back_populates="pill")
    responses: Mapped[list["ParticipantResponse"]] = relationship(back_populates="pill")


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    pill_id: Mapped[int | None] = mapped_column(ForeignKey("pills.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(30))
    provider_message_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    participant: Mapped[Participant] = relationship(back_populates="deliveries")
    pill: Mapped[Pill | None] = relationship(back_populates="deliveries")


class ParticipantResponse(Base):
    __tablename__ = "participant_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    pill_id: Mapped[int | None] = mapped_column(ForeignKey("pills.id"), nullable=True, index=True)
    message_body: Mapped[str] = mapped_column(Text)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=local_now)

    participant: Mapped[Participant] = relationship(back_populates="responses")
    pill: Mapped[Pill | None] = relationship(back_populates="responses")


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    easy_to_understand: Mapped[int] = mapped_column(Integer)
    learned_something: Mapped[bool] = mapped_column(Boolean)
    most_useful_content: Mapped[str] = mapped_column(Text)
    would_recommend: Mapped[bool] = mapped_column(Boolean)
    additional_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=local_now)

    participant: Mapped[Participant] = relationship(back_populates="feedbacks")
