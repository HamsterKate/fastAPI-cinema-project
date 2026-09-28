from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.favorites.models import FavoriteMovieModel
from app.movies.models import MovieModel


class FavoriteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def active_movie_exists(self, movie_id: UUID) -> bool:
        movie_id_in_db = await self.db.scalar(
            select(MovieModel.id).where(
                MovieModel.id == movie_id,
                MovieModel.deleted_at.is_(None),
            )
        )
        return movie_id_in_db is not None

    async def get_favorite(
        self,
        user_id: UUID,
        movie_id: UUID,
    ) -> FavoriteMovieModel | None:
        return await self.db.get(
            FavoriteMovieModel,
            (user_id, movie_id),
        )

    async def add(self, user_id: UUID, movie_id: UUID) -> bool:
        statement = (
            insert(FavoriteMovieModel)
            .values(user_id=user_id, movie_id=movie_id)
            .on_conflict_do_nothing(
                index_elements=["user_id", "movie_id"]
            )
            .returning(FavoriteMovieModel.movie_id)
        )
        inserted_movie_id = await self.db.scalar(statement)
        return inserted_movie_id is not None

    async def remove(self, favorite: FavoriteMovieModel) -> None:
        await self.db.delete(favorite)
        await self.db.flush()

    async def list_movies(
        self,
        user_id: UUID,
        page: int,
        per_page: int,
    ) -> tuple[list[MovieModel], int]:
        query = (
            select(MovieModel)
            .join(
                FavoriteMovieModel,
                FavoriteMovieModel.movie_id == MovieModel.id,
            )
            .where(
                FavoriteMovieModel.user_id == user_id,
                MovieModel.deleted_at.is_(None),
            )
        )

        total_items = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )

        result = await self.db.execute(
            query
            .order_by(
                FavoriteMovieModel.created_at.desc(),
                MovieModel.id.desc(),
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        return list(result.scalars().all()), total_items or 0


