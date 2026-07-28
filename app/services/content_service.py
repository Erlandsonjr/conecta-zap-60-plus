import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Pill

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTENT_PATH = PROJECT_ROOT / "data" / "pills.json"


def load_pills(db: Session, content_path: Path = DEFAULT_CONTENT_PATH) -> int:
    records = json.loads(content_path.read_text(encoding="utf-8"))
    created = 0
    for item in records:
        pill = db.scalar(select(Pill).where(Pill.order_number == item["order_number"]))
        if pill is None:
            db.add(Pill(**item, active=True))
            created += 1
        else:
            for field, value in item.items():
                setattr(pill, field, value)
    db.commit()
    return created


def get_active_pills(db: Session) -> list[Pill]:
    return list(
        db.scalars(select(Pill).where(Pill.active.is_(True)).order_by(Pill.order_number))
    )
