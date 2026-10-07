from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.orders.models import (
    OrderItemModel,
    OrderModel,
    OrderStatusEnum,
)


class OrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_orders(
        self,
        user_id: UUID,
        page: int,
        per_page: int,
    ) -> tuple[list[OrderModel], int]:
        query = select(OrderModel).where(
            OrderModel.user_id == user_id
        )

        total_items = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )

        statement = (
            query
            .order_by(OrderModel.created_at.desc(), OrderModel.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(statement)

        return list(result.scalars().all()), total_items or 0

    async def get_by_id(
        self,
        user_id: UUID,
        order_id: UUID,
    ) -> OrderModel | None:
        statement = (
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .where(
                OrderModel.id == order_id,
                OrderModel.user_id == user_id,
            )
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_paid_movie_ids(
        self,
        user_id: UUID,
        movie_ids: list[UUID],
    ) -> set[UUID]:
        statement = (
            select(OrderItemModel.movie_id)
            .join(OrderItemModel.order)
            .where(
                OrderModel.user_id == user_id,
                OrderModel.status == OrderStatusEnum.PAID,
                OrderItemModel.movie_id.in_(movie_ids),
            )
        )
        result = await self.db.execute(statement)
        return set(result.scalars().all())

    async def get_pending_movie_ids(
        self,
        user_id: UUID,
        movie_ids: list[UUID],
    ) -> set[UUID]:
        statement = (
            select(OrderItemModel.movie_id)
            .join(OrderItemModel.order)
            .where(
                OrderModel.user_id == user_id,
                OrderModel.status == OrderStatusEnum.PENDING,
                OrderItemModel.movie_id.in_(movie_ids),
            )
        )
        result = await self.db.execute(statement)
        return set(result.scalars().all())

    async def add_order(self, order: OrderModel) -> OrderModel:
        self.db.add(order)
        await self.db.flush()
        return order

    async def set_status(
        self,
        order: OrderModel,
        status: OrderStatusEnum,
    ) -> OrderModel:
        order.status = status
        await self.db.flush()
        return order
    