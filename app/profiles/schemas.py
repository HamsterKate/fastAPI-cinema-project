from datetime import date
from uuid import UUID

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.accounts.models import GenderEnum


class ProfileResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    first_name: str | None
    last_name: str | None
    avatar: str | None
    gender: GenderEnum | None
    date_of_birth: date | None
    info: str | None


class ProfileUpdateRequestSchema(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    gender: GenderEnum | None = None
    date_of_birth: date | None = None
    info: str | None = None

    @field_validator("first_name", "last_name", "info", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if not stripped:
            raise ValueError("Text fields cannot be blank")
        return stripped

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self
