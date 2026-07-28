import re

from pydantic import BaseModel, Field, field_validator


class ParticipantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=32)
    mode: str = "demo"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone must contain between 10 and 15 digits")
        if not digits.startswith("55"):
            digits = f"55{digits}"
        return f"+{digits}"

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        normalized = value.lower().strip()
        if normalized not in {"demo", "real"}:
            raise ValueError("Mode must be demo or real")
        return normalized


class FeedbackCreate(BaseModel):
    easy_to_understand: int = Field(ge=1, le=5)
    learned_something: bool
    most_useful_content: str = Field(min_length=1, max_length=500)
    would_recommend: bool
    additional_comment: str | None = Field(default=None, max_length=1000)
