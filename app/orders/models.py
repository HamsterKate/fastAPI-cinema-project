from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class OrderStatusEnum(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[OrderStatusEnum] = mapped_column(
        Enum(
            OrderStatusEnum,
            name="order_status_enum",
            native_enum=True,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=OrderStatusEnum.PENDING,
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["UserModel"] = relationship(
        back_populates="orders",
    )
    items: Mapped[list["OrderItemModel"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "total_price >= 0",
            name="total_price_non_negative",
        ),
        Index(
            "ix_orders_user_id_created_at",
            "user_id",
            "created_at",
        ),
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    movie_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("movies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    movie_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    order: Mapped["OrderModel"] = relationship(
        back_populates="items",
    )
    movie: Mapped["MovieModel"] = relationship(
        back_populates="order_items",
    )

    __table_args__ = (
        CheckConstraint(
            "unit_price >= 0",
            name="unit_price_non_negative",
        ),
        UniqueConstraint(
            "order_id",
            "movie_id",
            name="uq_order_items_order_id_movie_id",
        ),
        Index("ix_order_items_movie_id", "movie_id"),
    )
