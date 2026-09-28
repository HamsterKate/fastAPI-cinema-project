from decimal import Decimal
from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cart.repository import CartRepository
from app.orders.models import (
    OrderItemModel,
    OrderModel,
    OrderStatusEnum,
)
from app.orders.repository import OrderRepository
from app.orders.schemas import OrderListResponseSchema


class CartIsEmptyError(Exception):
    pass


class MovieUnavailableError(Exception):
    pass


class MoviesAlreadyPurchasedError(Exception):
    pass


class PendingOrderConflictError(Exception):
    pass


class OrderNotFoundError(Exception):
    pass


class OrderCannotBeCanceledError(Exception):
    pass


async def checkout(
    db: AsyncSession,
    user_id: UUID,
) -> OrderModel:
    cart_repository = CartRepository(db)
    order_repository = OrderRepository(db)

    cart = await cart_repository.get_cart_by_user_id(user_id)
    if cart is None or not cart.items:
        raise CartIsEmptyError("Cart is empty")

    if any(
        item.movie is None or item.movie.deleted_at is not None for item in cart.items
    ):
        raise MovieUnavailableError("One or more movies are no longer available")

    movie_ids = [item.movie_id for item in cart.items]

    purchased_movie_ids = await order_repository.get_paid_movie_ids(
        user_id,
        movie_ids,
    )
    if purchased_movie_ids:
        raise MoviesAlreadyPurchasedError("One or more movies are already purchased")

    pending_movie_ids = await order_repository.get_pending_movie_ids(
        user_id,
        movie_ids,
    )
    if pending_movie_ids:
        raise PendingOrderConflictError(
            "One or more movies already have a pending order"
        )

    total_price = sum(
        (item.movie.price for item in cart.items),
        start=Decimal("0.00"),
    )

    order = OrderModel(
        user_id=user_id,
        total_price=total_price,
        items=[
            OrderItemModel(
                movie_id=item.movie_id,
                movie_name=item.movie.name,
                unit_price=item.movie.price,
            )
            for item in cart.items
        ],
    )

    try:
        await order_repository.add_order(order)
        await cart_repository.clear_items(cart.id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    saved_order = await order_repository.get_by_id(user_id, order.id)
    assert saved_order is not None

    return saved_order


async def get_orders_page(
    db: AsyncSession,
    user_id: UUID,
    page: int,
    per_page: int,
    path: str,
) -> OrderListResponseSchema:
    repository = OrderRepository(db)
    orders, total_items = await repository.list_orders(
        user_id,
        page,
        per_page,
    )
    total_pages = (total_items + per_page - 1) // per_page

    def page_link(target_page: int) -> str:
        return f"{path}?{urlencode({'page': target_page, 'per_page': per_page})}"

    return OrderListResponseSchema(
        orders=orders,
        prev_page=page_link(page - 1) if page > 1 else None,
        next_page=(page_link(page + 1) if page < total_pages else None),
        total_pages=total_pages,
        total_items=total_items,
    )


async def get_order(
    db: AsyncSession,
    user_id: UUID,
    order_id: UUID,
) -> OrderModel:
    repository = OrderRepository(db)
    order = await repository.get_by_id(user_id, order_id)

    if order is None:
        raise OrderNotFoundError("Order not found")

    return order


async def cancel_order(
    db: AsyncSession,
    user_id: UUID,
    order_id: UUID,
) -> OrderModel:
    repository = OrderRepository(db)
    order = await repository.get_by_id(user_id, order_id)

    if order is None:
        raise OrderNotFoundError("Order not found")

    if order.status is not OrderStatusEnum.PENDING:
        raise OrderCannotBeCanceledError("Only pending orders can be canceled")

    try:
        await repository.set_status(order, OrderStatusEnum.CANCELED)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    saved_order = await repository.get_by_id(user_id, order_id)
    assert saved_order is not None

    return saved_order
