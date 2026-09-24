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


class MovieCreateResponseSchema(BaseModel):
    movie: MovieDetailSchema
    messages: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "movie": {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "name": "Example Movie",
                    "date": "2025-01-01",
                    "score": 80,
                    "overview": "A sample movie.",
                    "status": "Released",
                    "budget": "100.00",
                    "revenue": "200.00",
                    "country": {
                        "id": "22222222-2222-4222-8222-222222222222",
                        "code": "USA",
                        "name": None,
                    },
                    "genres": [
                        {
                            "id": "33333333-3333-4333-8333-333333333333",
                            "name": "Drama",
                        }
                    ],
                    "actors": [
                        {
                            "id": "44444444-4444-4444-8444-444444444444",
                            "name": "Example Actor",
                        }
                    ],
                    "languages": [
                        {
                            "id": "55555555-5555-4555-8555-555555555555",
                            "name": "English",
                        }
                    ],
                },
                "messages": [
                    "Genre 'DRAMA' was saved as 'Drama'."
                ],
            }
        }
    )


class ActorReferenceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_id_or_name(self) -> Self:
        if (self.id is None) == (self.name is None):
            raise ValueError("Provide exactly one of id or name")
        return self


class MovieCreateRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    date: Date
    score: float = Field(ge=0, le=100)
    overview: str = Field(min_length=1)
    status: MovieStatusEnum
    budget: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    revenue: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    country: str = Field(min_length=2, max_length=3)
    genres: list[str]
    actors: list[ActorReferenceSchema]
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

    @field_validator("languages")
    @classmethod
    def validate_related_names(cls, values: list[str]) -> list[str]:
        result = [value.strip() for value in values]
        if any(not value for value in result):
            raise ValueError("Names cannot be blank")
        return result

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Example Movie",
                "date": "2025-01-01",
                "score": 80,
                "overview": "A sample movie.",
                "status": "Released",
                "budget": "100.00",
                "revenue": "200.00",
                "country": "US",
                "genres": ["DRAMA", "Non-Fiction"],
                "actors": [{"name": "Example Actor"}],
                "languages": ["English"],
            }
        }
    )


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
