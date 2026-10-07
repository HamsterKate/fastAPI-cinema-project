from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.orders.models import OrderStatusEnum


class OrderItemResponseSchema(BaseModel):
    id: UUID
    movie_id: UUID
    movie_name: str
    unit_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderListItemSchema(BaseModel):
    id: UUID
    status: OrderStatusEnum
    total_price: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderDetailSchema(OrderListItemSchema):
    updated_at: datetime
    items: list[OrderItemResponseSchema]


class OrderListResponseSchema(BaseModel):
    orders: list[OrderListItemSchema]
    prev_page: str | None
    next_page: str | None
    total_pages: int = Field(ge=0)
    total_items: int = Field(ge=0)
