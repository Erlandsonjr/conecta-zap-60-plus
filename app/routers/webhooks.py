from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.config import Settings, get_settings
from app.database import get_db
from app.models import Delivery
from app.services.automation_service import AutomationService
from app.services.messaging.twilio_provider import create_provider

router = APIRouter(prefix="/webhooks/twilio")


def validate_signature(
    request: Request,
    form: dict[str, str],
    settings: Settings,
) -> None:
    if not settings.twilio_validate_signature:
        return
    if not settings.twilio_auth_token:
        raise HTTPException(status_code=500, detail="Twilio signature validation is not configured")
    signature = request.headers.get("X-Twilio-Signature", "")
    validator = RequestValidator(settings.twilio_auth_token)
    if not signature or not validator.validate(str(request.url), form, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")


@router.post("/incoming")
async def incoming_message(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    raw_form = await request.form()
    form = {key: str(value) for key, value in raw_form.items()}
    validate_signature(request, form, settings)

    sender = form.get("From", "")
    body = form.get("Body", "")
    _recipient = form.get("To", "")
    _message_sid = form.get("MessageSid", "")
    if not sender:
        raise HTTPException(status_code=422, detail="From is required")
    num_media = int(form.get("NumMedia", "0") or 0)
    media_url = form.get("MediaUrl0") if num_media > 0 else None

    service = AutomationService(db, create_provider(settings), settings)
    service.process_incoming(sender, body, media_url)
    twiml = MessagingResponse()
    return Response(content=str(twiml), media_type="application/xml")


@router.post("/status")
async def delivery_status(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    raw_form = await request.form()
    form = {key: str(value) for key, value in raw_form.items()}
    validate_signature(request, form, settings)

    message_sid = form.get("MessageSid", "")
    status = form.get("MessageStatus", "").lower()
    delivery = db.scalar(
        select(Delivery).where(Delivery.provider_message_id == message_sid)
    )
    if delivery and status:
        delivery.status = status
        from app.models import local_now

        if status == "delivered":
            delivery.delivered_at = local_now()
        elif status == "read":
            delivery.read_at = local_now()
        elif status in {"failed", "undelivered"}:
            delivery.error_message = form.get("ErrorMessage") or form.get("ErrorCode")
        db.commit()
    return Response(content="<Response></Response>", media_type="application/xml")
