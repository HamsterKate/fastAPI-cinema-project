from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.favorites.services import (
    FavoriteAlreadyExistsError,
    FavoriteMovieNotFoundError,
    FavoriteNotFoundError,
    add_favorite,
    get_favorites_page,
    remove_favorite,
)


def mock_favorite_repository(
    monkeypatch: pytest.MonkeyPatch,
    *,
    active_movie_exists: bool = True,
    favorite: object | None = None,
    add_result: bool = True,
) -> None:
    class FakeFavoriteRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def active_movie_exists(
            self,
            movie_id: object,
        ) -> bool:
            return active_movie_exists

        async def get_favorite(
            self,
            user_id: object,
            movie_id: object,
        ) -> object | None:
            return favorite

        async def add(
            self,
            user_id: object,
            movie_id: object,
        ) -> bool:
            return add_result

        async def remove(self, current_favorite: object) -> None:
            return None

    monkeypatch.setattr(
        "app.favorites.services.FavoriteRepository",
        FakeFavoriteRepository,
    )


@pytest.mark.asyncio
async def test_add_favorite_rejects_missing_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_favorite_repository(
        monkeypatch,
        active_movie_exists=False,
    )

    with pytest.raises(FavoriteMovieNotFoundError):
        await add_favorite(
            SimpleNamespace(),
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_add_favorite_rejects_existing_favorite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_favorite_repository(
        monkeypatch,
        favorite=SimpleNamespace(),
    )

    with pytest.raises(FavoriteAlreadyExistsError):
        await add_favorite(
            SimpleNamespace(),
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_add_favorite_rejects_concurrent_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_favorite_repository(
        monkeypatch,
        add_result=False,
    )

    with pytest.raises(FavoriteAlreadyExistsError):
        await add_favorite(
            SimpleNamespace(),
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_add_favorite_commits_new_favorite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = SimpleNamespace(commit=AsyncMock())
    mock_favorite_repository(monkeypatch)

    await add_favorite(db, uuid4(), uuid4())

    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_favorite_rejects_missing_favorite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_favorite_repository(monkeypatch)

    with pytest.raises(FavoriteNotFoundError):
        await remove_favorite(
            SimpleNamespace(),
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_remove_favorite_deletes_and_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    favorite = SimpleNamespace()
    removed_favorites: list[object] = []

    class FakeFavoriteRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_favorite(
            self,
            user_id: object,
            movie_id: object,
        ) -> object:
            return favorite

        async def remove(self, current_favorite: object) -> None:
            removed_favorites.append(current_favorite)

    db = SimpleNamespace(commit=AsyncMock())

    monkeypatch.setattr(
        "app.favorites.services.FavoriteRepository",
        FakeFavoriteRepository,
    )

    await remove_favorite(db, uuid4(), uuid4())

    assert removed_favorites == [favorite]
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_favorites_page_returns_empty_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeFavoriteRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def list_movies(
            self,
            user_id: object,
            page: int,
            per_page: int,
        ) -> tuple[list[object], int]:
            return [], 0

    monkeypatch.setattr(
        "app.favorites.services.FavoriteRepository",
        FakeFavoriteRepository,
    )

    response = await get_favorites_page(
        SimpleNamespace(),
        uuid4(),
        page=1,
        per_page=10,
        path="/api/v2/favorites",
    )

    assert response.movies == []
    assert response.total_items == 0
    assert response.total_pages == 0
    assert response.prev_page is None
    assert response.next_page is None
