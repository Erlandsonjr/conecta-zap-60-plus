from urllib.parse import quote

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import Participant
from app.schemas import ParticipantCreate

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@router.post("/participants")
def create_participant(
    name: str = Form(...),
    phone: str = Form(...),
    mode: str = Form("demo"),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        data = ParticipantCreate(name=name, phone=phone, mode=mode)
        participant = Participant(name=data.name, phone=data.phone, mode=data.mode)
        db.add(participant)
        db.commit()
        message = quote("Participante cadastrado com sucesso.")
        return RedirectResponse(f"/admin/participants?success={message}", status_code=303)
    except ValidationError as exc:
        message = quote(exc.errors()[0]["msg"])
        return RedirectResponse(f"/admin/participants?error={message}", status_code=303)
    except IntegrityError:
        db.rollback()
        message = quote("Já existe um participante com esse telefone.")
        return RedirectResponse(f"/admin/participants?error={message}", status_code=303)
