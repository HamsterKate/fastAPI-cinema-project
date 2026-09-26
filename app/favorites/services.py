from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import build_pagination_links
from app.favorites.repository import FavoriteRepository
from app.movies.schemas import MovieListResponseSchema


class FavoriteMovieNotFoundError(Exception):
    pass


class FavoriteAlreadyExistsError(Exception):
    pass


class FavoriteNotFoundError(Exception):
    pass


async def add_favorite(
    db: AsyncSession,
    user_id: UUID,
    movie_id: UUID,
) -> None:
    repository = FavoriteRepository(db)

    if not await repository.active_movie_exists(movie_id):
        raise FavoriteMovieNotFoundError

    if await repository.get_favorite(user_id, movie_id):
        raise FavoriteAlreadyExistsError

    if not await repository.add(user_id, movie_id):
        raise FavoriteAlreadyExistsError

    await db.commit()


async def remove_favorite(
    db: AsyncSession,
    user_id: UUID,
    movie_id: UUID,
) -> None:
    repository = FavoriteRepository(db)
    favorite = await repository.get_favorite(user_id, movie_id)

    if favorite is None:
        raise FavoriteNotFoundError

    await repository.remove(favorite)
    await db.commit()


async def get_favorites_page(
        db: AsyncSession,
        user_id: UUID,
        page: int,
        per_page: int,
        path: str,
) -> MovieListResponseSchema:
    repository = FavoriteRepository(db)
    movies, total_items = await repository.list_movies(user_id, page, per_page)

    prev_page, next_page, total_pages = build_pagination_links(
        path,
        page,
        per_page,
        total_items,
    )

    return MovieListResponseSchema(
        movies=movies,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items,
    )
