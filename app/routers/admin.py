from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import require_admin
from app.models import Delivery, Participant, Pill
from app.services.automation_service import AutomationService, dashboard_counts
from app.services.messaging.twilio_provider import create_provider

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory="app/templates")


def mask_phone(phone: str) -> str:
    if len(phone) < 8:
        return "***"
    return f"{phone[:3]} ••••• {phone[-4:]}"


def format_datetime(value: datetime | None) -> str:
    return value.strftime("%d/%m/%Y %H:%M") if value else "—"


templates.env.filters["mask_phone"] = mask_phone
templates.env.filters["datetime"] = format_datetime

STATIC_IMAGES_DIRECTORY = Path(__file__).resolve().parents[1] / "static" / "images"


def has_pill_image(filename: str | None) -> bool:
    if not filename:
        return False
    image_path = Path(filename)
    return (
        image_path.name == filename
        and image_path.suffix.lower() == ".png"
        and (STATIC_IMAGES_DIRECTORY / image_path.name).is_file()
    )


def get_participant_or_404(db: Session, participant_id: int) -> Participant:
    participant = db.scalar(
        select(Participant)
        .where(Participant.id == participant_id)
        .options(
            selectinload(Participant.deliveries).selectinload(Delivery.pill),
            selectinload(Participant.responses),
            selectinload(Participant.feedbacks),
        )
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    return participant


def redirect_detail(
    participant_id: int,
    *,
    success: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    key, value = ("success", success) if success else ("error", error)
    return RedirectResponse(
        f"/admin/participants/{participant_id}?{key}={quote(value or '')}",
        status_code=303,
    )


def service_for(db: Session, settings: Settings) -> AutomationService:
    return AutomationService(db, create_provider(settings), settings)


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    participants = list(
        db.scalars(select(Participant).order_by(Participant.created_at.desc()).limit(8))
    )
    context = {
        "request": request,
        "page_title": "Visão geral",
        "stats": dashboard_counts(db),
        "participants": participants,
    }
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)


@router.get("/participants", response_class=HTMLResponse)
def participants_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    participants = list(
        db.scalars(select(Participant).order_by(Participant.created_at.desc()))
    )
    return templates.TemplateResponse(
        request=request,
        name="participants.html",
        context={
            "request": request,
            "page_title": "Participantes",
            "participants": participants,
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/participants/{participant_id}", response_class=HTMLResponse)
def participant_detail(
    participant_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    participant = get_participant_or_404(db, participant_id)
    pills = list(db.scalars(select(Pill).order_by(Pill.order_number)))
    deliveries = sorted(
        participant.deliveries,
        key=lambda delivery: (delivery.sent_at or datetime.min, delivery.id),
        reverse=True,
    )
    responses = sorted(
        participant.responses,
        key=lambda response: response.received_at,
        reverse=True,
    )
    sent_pill_ids = {
        delivery.pill_id
        for delivery in participant.deliveries
        if delivery.pill_id and delivery.status != "failed"
    }
    return templates.TemplateResponse(
        request=request,
        name="participant_detail.html",
        context={
            "request": request,
            "page_title": participant.name,
            "participant": participant,
            "deliveries": deliveries,
            "responses": responses,
            "pills": pills,
            "sent_pill_ids": sent_pill_ids,
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/participants/{participant_id}/send-next")
def send_next(
    participant_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    participant = get_participant_or_404(db, participant_id)
    try:
        delivery = service_for(db, settings).send_next_pill(participant)
        pill_number = delivery.pill.order_number if delivery.pill else ""
        return redirect_detail(participant_id, success=f"Pílula {pill_number} enviada.")
    except ValueError as exc:
        return redirect_detail(participant_id, error=str(exc))


@router.post("/participants/{participant_id}/run-demo")
def run_demo(
    participant_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    participant = get_participant_or_404(db, participant_id)
    try:
        sent = service_for(db, settings).run_demo(participant)
        return redirect_detail(
            participant_id,
            success=f"Demonstração concluída com {sent} nova(s) pílula(s).",
        )
    except ValueError as exc:
        return redirect_detail(participant_id, error=str(exc))


@router.post("/participants/{participant_id}/pause")
def pause(participant_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    participant = get_participant_or_404(db, participant_id)
    participant.active = False
    participant.next_delivery_at = None
    db.commit()
    return redirect_detail(participant_id, success="Envios pausados.")


@router.post("/participants/{participant_id}/resume")
def resume(
    participant_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    participant = get_participant_or_404(db, participant_id)
    try:
        service_for(db, settings).resume_participant(participant)
        return redirect_detail(participant_id, success="Envios retomados.")
    except ValueError as exc:
        return redirect_detail(participant_id, error=str(exc))


@router.post("/participants/{participant_id}/reset")
def reset(
    participant_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    participant = get_participant_or_404(db, participant_id)
    service_for(db, settings).reset_participant(participant)
    return redirect_detail(participant_id, success="Trilha reiniciada e histórico removido.")


@router.post("/participants/{participant_id}/resend/{pill_id}")
def resend(
    participant_id: int,
    pill_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    participant = get_participant_or_404(db, participant_id)
    pill = db.get(Pill, pill_id)
    if pill is None:
        raise HTTPException(status_code=404, detail="Pill not found")
    delivery = service_for(db, settings).send_pill(participant, pill, force=True)
    db.commit()
    if delivery.status == "failed":
        return redirect_detail(participant_id, error="Não foi possível reenviar a pílula.")
    return redirect_detail(participant_id, success=f"Pílula {pill.order_number} reenviada.")


@router.get("/pills", response_class=HTMLResponse)
def pills_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    pills = list(db.scalars(select(Pill).order_by(Pill.order_number)))
    available_image_filenames = {
        pill.image_filename
        for pill in pills
        if has_pill_image(pill.image_filename)
    }
    return templates.TemplateResponse(
        request=request,
        name="pills.html",
        context={
            "request": request,
            "page_title": "Pílulas",
            "pills": pills,
            "available_image_filenames": available_image_filenames,
        },
    )
