from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.movies.schemas import GenreSchema


class CartMovieSchema(BaseModel):
    id: UUID
    name: str
    date: date
    price: Decimal
    genres: list[GenreSchema]

    model_config = ConfigDict(from_attributes=True)


class CartItemResponseSchema(BaseModel):
    id: UUID
    added_at: datetime
    movie: CartMovieSchema

    model_config = ConfigDict(from_attributes=True)


class CartResponseSchema(BaseModel):
    id: UUID
    items: list[CartItemResponseSchema]
    total_items: int = Field(ge=0)
    total_price: Decimal = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)
