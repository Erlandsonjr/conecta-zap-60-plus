import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import SessionLocal, create_database
from app.routers import admin, participants, webhooks
from app.services.content_service import load_pills
from app.services.scheduler_service import SchedulerService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

settings = get_settings()
scheduler_service = SchedulerService(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_database()
    with SessionLocal() as db:
        load_pills(db)
    if settings.scheduler_enabled:
        scheduler_service.start()
    yield
    scheduler_service.shutdown()


app = FastAPI(
    title="Conecta-Zap 60+",
    description="Academic prototype for digital safety education over WhatsApp",
    version="1.0.0",
    lifespan=lifespan,
)
static_directory = Path(__file__).parent / "static"
static_directory.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_directory), name="static")

app.include_router(admin.router)
app.include_router(participants.router)
app.include_router(webhooks.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/admin", status_code=307)
