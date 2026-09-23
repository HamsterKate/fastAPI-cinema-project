from datetime import date as Date, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.movies.models import MovieStatusEnum
from app.movies.validators import normalize_country_code


class CatalogReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GenreSchema(CatalogReadSchema):
    id: UUID
    name: str


class ActorSchema(CatalogReadSchema):
    id: UUID
    name: str


class CountrySchema(CatalogReadSchema):
    id: UUID
    code: str
    name: str | None


class LanguageSchema(CatalogReadSchema):
    id: UUID
    name: str


class MovieListItemSchema(CatalogReadSchema):
    id: UUID
    name: str
    date: Date
    score: float
    overview: str


class MovieDetailSchema(MovieListItemSchema):
    status: MovieStatusEnum
    budget: Decimal
    revenue: Decimal
    country: CountrySchema
    genres: list[GenreSchema]
    actors: list[ActorSchema]
    languages: list[LanguageSchema]


class MovieCreateRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    date: Date
    score: float = Field(ge=0, le=100)
    overview: str = Field(min_length=1)
    status: MovieStatusEnum
    budget: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    revenue: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    country: str = Field(min_length=3, max_length=3)
    genres: list[str]
    actors: list[str]
    languages: list[str]

    @field_validator("date")
    @classmethod
    def validate_release_date(cls, value: Date) -> Date:
        if value.year > datetime.now().year + 1:
            raise ValueError("Release date cannot be later than next year")
        return value

    @field_validator("name", "overview", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("country", mode="before")
    @classmethod
    def normalize_country(cls, value: object) -> object:
        return normalize_country_code(value) if isinstance(value, str) else value

    @field_validator("genres")
    @classmethod
    def validate_genres(cls, values: list[str]) -> list[str]:
        result = [value.strip() for value in values]
        if any(not value for value in result):
            raise ValueError("Genre names cannot be blank")
        return result

    @field_validator("actors", "languages")
    @classmethod
    def validate_related_names(cls, values: list[str]) -> list[str]:
        result = [value.strip() for value in values]
        if any(not value for value in result):
            raise ValueError("Names cannot be blank")
        return result


class MovieUpdateRequestSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    date: Date | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    overview: str | None = Field(default=None, min_length=1)
    status: MovieStatusEnum | None = None
    budget: Decimal | None = Field(
        default=None, ge=0, max_digits=15, decimal_places=2
    )
    revenue: Decimal | None = Field(
        default=None, ge=0, max_digits=15, decimal_places=2
    )

    @field_validator("name", "overview", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("date")
    @classmethod
    def validate_release_date(cls, value: Date | None) -> Date | None:
        if value is not None and value.year > datetime.now().year + 1:
            raise ValueError("Release date cannot be later than next year")
        return value

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")

        return self


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: str | None
    next_page: str | None
    total_pages: int = Field(ge=0)
    total_items: int = Field(ge=0)
