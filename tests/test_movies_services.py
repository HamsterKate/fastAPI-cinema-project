from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.movies.schemas import ActorReferenceSchema
from app.movies.services import (
    ActorNotFoundError,
    AmbiguousActorError,
    MovieNotFoundError,
    delete_movie,
    resolve_languages,
    update_movie,
    resolve_actors,
    resolve_genres,
)


@pytest.mark.asyncio
async def test_resolve_actors_rejects_unknown_actor_id() -> None:
    actor_id = uuid4()
    repository = SimpleNamespace(
        get_actor_by_id=AsyncMock(return_value=None),
    )

    with pytest.raises(
        ActorNotFoundError,
        match=f"Actor {actor_id} was not found",
    ):
        await resolve_actors(
            repository,
            [ActorReferenceSchema(id=actor_id)],
        )


@pytest.mark.asyncio
async def test_resolve_actors_rejects_ambiguous_name() -> None:
    repository = SimpleNamespace(
        find_actors_by_name=AsyncMock(
            return_value=[
                SimpleNamespace(id=uuid4()),
                SimpleNamespace(id=uuid4()),
            ],
        ),
    )

    with pytest.raises(
        AmbiguousActorError,
        match="provide an actor ID",
    ):
        await resolve_actors(
            repository,
            [ActorReferenceSchema(name="Alex")],
        )


@pytest.mark.asyncio
async def test_resolve_actors_creates_and_deduplicates_actor() -> None:
    actor = SimpleNamespace(id=uuid4(), name="Kate")
    repository = SimpleNamespace(
        find_actors_by_name=AsyncMock(return_value=[]),
        create_actor=AsyncMock(return_value=actor),
    )

    result = await resolve_actors(
        repository,
        [
            ActorReferenceSchema(name="Kate"),
            ActorReferenceSchema(name="Kate"),
        ],
    )

    assert result == [actor]
    assert repository.create_actor.await_count == 2


@pytest.mark.asyncio
async def test_resolve_genres_normalizes_names_and_returns_messages() -> None:
    genre = SimpleNamespace(id=uuid4(), name="Drama")
    repository = SimpleNamespace(
        get_or_create_genre=AsyncMock(return_value=genre),
    )

    genres, messages = await resolve_genres(
        repository,
        ["DRAMA", "Drama"],
    )

    assert genres == [genre]
    assert messages == [
        "Genre 'DRAMA' was saved as 'Drama'.",
    ]
    assert repository.get_or_create_genre.await_count == 2


@pytest.mark.asyncio
async def test_resolve_languages_deduplicates_related_records() -> None:
    language = SimpleNamespace(id=uuid4(), name="English")
    repository = SimpleNamespace(
        get_or_create_language=AsyncMock(
            return_value=language,
        ),
    )

    result = await resolve_languages(
        repository,
        ["English", "English"],
    )

    assert result == [language]
    assert repository.get_or_create_language.await_count == 2


@pytest.mark.asyncio
async def test_update_movie_rejects_missing_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMovieRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_id(
            self,
            movie_id: object,
        ) -> None:
            return None

    monkeypatch.setattr(
        "app.movies.services.MovieRepository",
        FakeMovieRepository,
    )

    with pytest.raises(
        MovieNotFoundError,
        match="Movie not found",
    ):
        await update_movie(
            SimpleNamespace(),
            uuid4(),
            SimpleNamespace(model_dump=lambda **kwargs: {}),
        )


@pytest.mark.asyncio
async def test_delete_movie_rejects_missing_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMovieRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_id(
            self,
            movie_id: object,
        ) -> None:
            return None

    monkeypatch.setattr(
        "app.movies.services.MovieRepository",
        FakeMovieRepository,
    )

    with pytest.raises(
        MovieNotFoundError,
        match="Movie not found",
    ):
        await delete_movie(
            SimpleNamespace(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_update_movie_saves_changes_and_returns_updated_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    movie_id = uuid4()
    movie = SimpleNamespace(id=movie_id)
    updated_movie = SimpleNamespace(
        id=movie_id,
        score=95,
    )
    updated_changes: list[dict[str, object]] = []

    class FakeMovieRepository:
        def __init__(self, db: object) -> None:
            self.db = db
            self.get_calls = 0

        async def get_by_id(
            self,
            current_movie_id: object,
        ) -> object:
            self.get_calls += 1
            return movie if self.get_calls == 1 else updated_movie

        async def update_movie(
            self,
            current_movie: object,
            changes: dict[str, object],
        ) -> None:
            updated_changes.append(changes)

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    monkeypatch.setattr(
        "app.movies.services.MovieRepository",
        FakeMovieRepository,
    )

    result = await update_movie(
        db,
        movie_id,
        SimpleNamespace(
            model_dump=lambda **kwargs: {"score": 95},
        ),
    )

    assert result is updated_movie
    assert updated_changes == [{"score": 95}]
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_movie_marks_movie_as_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    movie_id = uuid4()
    movie = SimpleNamespace(id=movie_id)
    deleted_movies: list[object] = []

    class FakeMovieRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_id(
            self,
            current_movie_id: object,
        ) -> object:
            return movie

        async def mark_deleted(
            self,
            current_movie: object,
            deleted_at: object,
        ) -> None:
            deleted_movies.append(current_movie)

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    monkeypatch.setattr(
        "app.movies.services.MovieRepository",
        FakeMovieRepository,
    )

    await delete_movie(db, movie_id)

    assert deleted_movies == [movie]
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
