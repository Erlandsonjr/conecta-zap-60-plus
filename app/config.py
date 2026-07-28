from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    app_env: str = "development"
    app_timezone: str = "America/Sao_Paulo"
    database_url: str = "sqlite:///./conecta_zap.db"
    messaging_provider: str = "mock"
    base_url: str = "http://localhost:8000"
    demo_interval_minutes: int = Field(default=2, ge=1)
    real_delivery_hour: int = Field(default=9, ge=0, le=23)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"
    twilio_validate_signature: bool = False
    admin_username: str = "admin"
    admin_password: str = "change-me"
    scheduler_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @field_validator("messaging_provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        normalized = value.lower().strip()
        if normalized not in {"mock", "twilio"}:
            raise ValueError("MESSAGING_PROVIDER must be 'mock' or 'twilio'")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
