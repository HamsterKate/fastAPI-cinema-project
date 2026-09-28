from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.cart.services import (
    CartItemAlreadyExistsError,
    CartItemNotFoundError,
    CartMovieNotFoundError,
    add_movie_to_cart,
    get_or_create_cart,
    remove_movie_from_cart,
)


@pytest.mark.asyncio
async def test_get_or_create_cart_returns_existing_cart() -> None:
    user_id = uuid4()
    cart = SimpleNamespace(id=uuid4())
    repository = SimpleNamespace(
        get_cart_by_user_id=AsyncMock(return_value=cart),
        create_cart=AsyncMock(),
    )

    result = await get_or_create_cart(repository, user_id)

    assert result is cart
    repository.create_cart.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_cart_creates_missing_cart() -> None:
    user_id = uuid4()
    cart = SimpleNamespace(id=uuid4())
    repository = SimpleNamespace(
        get_cart_by_user_id=AsyncMock(return_value=None),
        create_cart=AsyncMock(return_value=cart),
    )

    result = await get_or_create_cart(repository, user_id)

    assert result is cart
    repository.create_cart.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_add_movie_to_cart_rejects_missing_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cart = SimpleNamespace(id=uuid4())

    class FakeCartRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_cart_by_user_id(
            self,
            user_id: object,
        ) -> object:
            return cart

        async def get_available_movie_by_id(
            self,
            movie_id: object,
        ) -> None:
            return None

    monkeypatch.setattr(
        "app.cart.services.CartRepository",
        FakeCartRepository,
    )

    with pytest.raises(
        CartMovieNotFoundError,
        match="Movie not found",
    ):
        await add_movie_to_cart(
            SimpleNamespace(),
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_remove_movie_from_cart_rejects_missing_cart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeCartRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_cart_by_user_id(
            self,
            user_id: object,
        ) -> None:
            return None

    monkeypatch.setattr(
        "app.cart.services.CartRepository",
        FakeCartRepository,
    )

    with pytest.raises(
        CartItemNotFoundError,
        match="Movie is not in the cart",
    ):
        await remove_movie_from_cart(
            SimpleNamespace(),
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_add_movie_to_cart_rejects_duplicate_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cart = SimpleNamespace(id=uuid4())

    class FakeCartRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_cart_by_user_id(
            self,
            user_id: object,
        ) -> object:
            return cart

        async def get_available_movie_by_id(
            self,
            movie_id: object,
        ) -> object:
            return SimpleNamespace()

        async def get_item(
            self,
            cart_id: object,
            movie_id: object,
        ) -> object:
            return SimpleNamespace()

    monkeypatch.setattr(
        "app.cart.services.CartRepository",
        FakeCartRepository,
    )

    with pytest.raises(
        CartItemAlreadyExistsError,
        match="Movie is already in the cart",
    ):
        await add_movie_to_cart(
            SimpleNamespace(),
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_remove_movie_from_cart_rejects_missing_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cart = SimpleNamespace(id=uuid4())

    class FakeCartRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_cart_by_user_id(
            self,
            user_id: object,
        ) -> object:
            return cart

        async def get_item(
            self,
            cart_id: object,
            movie_id: object,
        ) -> None:
            return None

    monkeypatch.setattr(
        "app.cart.services.CartRepository",
        FakeCartRepository,
    )

    with pytest.raises(
        CartItemNotFoundError,
        match="Movie is not in the cart",
    ):
        await remove_movie_from_cart(
            SimpleNamespace(),
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_add_movie_to_cart_saves_item_and_returns_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    movie_id = uuid4()
    cart = SimpleNamespace(id=uuid4())
    added_items: list[tuple[object, object]] = []
    expected_response = SimpleNamespace(total_items=1)

    class FakeCartRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_cart_by_user_id(
            self,
            current_user_id: object,
        ) -> object:
            return cart

        async def get_available_movie_by_id(
            self,
            current_movie_id: object,
        ) -> object:
            return SimpleNamespace()

        async def get_item(
            self,
            cart_id: object,
            current_movie_id: object,
        ) -> None:
            return None

        async def add_item(
            self,
            cart_id: object,
            current_movie_id: object,
        ) -> None:
            added_items.append((cart_id, current_movie_id))

    db = SimpleNamespace(commit=AsyncMock())

    monkeypatch.setattr(
        "app.cart.services.CartRepository",
        FakeCartRepository,
    )
    monkeypatch.setattr(
        "app.cart.services.build_cart_response",
        lambda saved_cart: expected_response,
    )

    response = await add_movie_to_cart(
        db,
        user_id,
        movie_id,
    )

    assert response is expected_response
    assert added_items == [(cart.id, movie_id)]
    db.commit.assert_awaited_once()
