from types import SimpleNamespace
from uuid import uuid4
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.orders.models import OrderStatusEnum
from app.orders.services import (
    CartIsEmptyError,
    MovieUnavailableError,
    MoviesAlreadyPurchasedError,
    OrderCannotBeCanceledError,
    OrderNotFoundError,
    cancel_order,
    checkout,
    PendingOrderConflictError,
)


def mock_checkout_repositories(
    monkeypatch: pytest.MonkeyPatch,
    cart: object,
    paid_movie_ids: set[object] | None = None,
    pending_movie_ids: set[object] | None = None,
) -> None:
    class FakeCartRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_cart_by_user_id(
            self,
            user_id: object,
        ) -> object:
            return cart

    class FakeOrderRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_paid_movie_ids(
            self,
            user_id: object,
            movie_ids: list[object],
        ) -> set[object]:
            return paid_movie_ids or set()

        async def get_pending_movie_ids(
            self,
            user_id: object,
            movie_ids: list[object],
        ) -> set[object]:
            return pending_movie_ids or set()

    monkeypatch.setattr(
        "app.orders.services.CartRepository",
        FakeCartRepository,
    )
    monkeypatch.setattr(
        "app.orders.services.OrderRepository",
        FakeOrderRepository,
    )


@pytest.mark.asyncio
async def test_checkout_rejects_empty_cart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_checkout_repositories(monkeypatch, cart=None)

    with pytest.raises(
        CartIsEmptyError,
        match="Cart is empty",
    ):
        await checkout(SimpleNamespace(), uuid4())


@pytest.mark.asyncio
async def test_checkout_rejects_unavailable_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cart = SimpleNamespace(
        items=[
            SimpleNamespace(
                movie_id=uuid4(),
                movie=None,
            ),
        ],
    )
    mock_checkout_repositories(monkeypatch, cart)

    with pytest.raises(
        MovieUnavailableError,
        match="One or more movies are no longer available",
    ):
        await checkout(SimpleNamespace(), uuid4())


@pytest.mark.asyncio
async def test_checkout_rejects_already_purchased_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    movie_id = uuid4()
    cart = SimpleNamespace(
        items=[
            SimpleNamespace(
                movie_id=movie_id,
                movie=SimpleNamespace(
                    deleted_at=None,
                ),
            ),
        ],
    )
    mock_checkout_repositories(
        monkeypatch,
        cart,
        paid_movie_ids={movie_id},
    )

    with pytest.raises(
        MoviesAlreadyPurchasedError,
        match="One or more movies are already purchased",
    ):
        await checkout(SimpleNamespace(), uuid4())


@pytest.mark.asyncio
async def test_checkout_rejects_movie_with_pending_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    movie_id = uuid4()
    cart = SimpleNamespace(
        items=[
            SimpleNamespace(
                movie_id=movie_id,
                movie=SimpleNamespace(
                    deleted_at=None,
                ),
            ),
        ],
    )
    mock_checkout_repositories(
        monkeypatch,
        cart,
        pending_movie_ids={movie_id},
    )

    with pytest.raises(
        PendingOrderConflictError,
        match="One or more movies already have a pending order",
    ):
        await checkout(SimpleNamespace(), uuid4())


@pytest.mark.asyncio
async def test_checkout_creates_order_and_clears_cart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    movie_id = uuid4()
    order_id = uuid4()
    cart = SimpleNamespace(
        id=uuid4(),
        items=[
            SimpleNamespace(
                movie_id=movie_id,
                movie=SimpleNamespace(
                    deleted_at=None,
                    name="Test movie",
                    price=Decimal("9.99"),
                ),
            ),
        ],
    )
    cleared_cart_ids: list[object] = []
    created_orders: list[object] = []

    class FakeCartRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_cart_by_user_id(
            self,
            current_user_id: object,
        ) -> object:
            return cart

        async def clear_items(self, cart_id: object) -> None:
            cleared_cart_ids.append(cart_id)

    class FakeOrderRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_paid_movie_ids(
            self,
            current_user_id: object,
            movie_ids: list[object],
        ) -> set[object]:
            return set()

        async def get_pending_movie_ids(
            self,
            current_user_id: object,
            movie_ids: list[object],
        ) -> set[object]:
            return set()

        async def add_order(self, order: object) -> None:
            order.id = order_id
            created_orders.append(order)

        async def get_by_id(
            self,
            current_user_id: object,
            current_order_id: object,
        ) -> object:
            return created_orders[0]

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    monkeypatch.setattr(
        "app.orders.services.CartRepository",
        FakeCartRepository,
    )
    monkeypatch.setattr(
        "app.orders.services.OrderRepository",
        FakeOrderRepository,
    )

    order = await checkout(db, user_id)

    assert order.id == order_id
    assert order.total_price == Decimal("9.99")
    assert cleared_cart_ids == [cart.id]
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_order_rejects_missing_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeOrderRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_id(
            self,
            user_id: object,
            order_id: object,
        ) -> None:
            return None

    monkeypatch.setattr(
        "app.orders.services.OrderRepository",
        FakeOrderRepository,
    )

    with pytest.raises(
        OrderNotFoundError,
        match="Order not found",
    ):
        await cancel_order(
            SimpleNamespace(),
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_cancel_order_rejects_non_pending_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = SimpleNamespace(status=OrderStatusEnum.PAID)

    class FakeOrderRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_id(
            self,
            user_id: object,
            order_id: object,
        ) -> object:
            return order

    monkeypatch.setattr(
        "app.orders.services.OrderRepository",
        FakeOrderRepository,
    )

    with pytest.raises(
        OrderCannotBeCanceledError,
        match="Only pending orders can be canceled",
    ):
        await cancel_order(
            SimpleNamespace(),
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_cancel_order_updates_pending_order_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = SimpleNamespace(status=OrderStatusEnum.PENDING)

    class FakeOrderRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_id(
            self,
            user_id: object,
            order_id: object,
        ) -> object:
            return order

        async def set_status(
            self,
            current_order: object,
            status: OrderStatusEnum,
        ) -> None:
            current_order.status = status

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    monkeypatch.setattr(
        "app.orders.services.OrderRepository",
        FakeOrderRepository,
    )

    result = await cancel_order(
        db,
        uuid4(),
        uuid4(),
    )

    assert result is order
    assert result.status is OrderStatusEnum.CANCELED
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
