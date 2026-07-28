import os
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

TEST_DATABASE = Path(__file__).resolve().parents[1] / "test_conecta_zap.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE.as_posix()}"
os.environ["MESSAGING_PROVIDER"] = "mock"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-password"

from app.database import Base, SessionLocal, engine
from app.services.content_service import load_pills


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        load_pills(db)
    yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db


@pytest.fixture
def admin_auth() -> tuple[str, str]:
    return ("admin", "test-password")
