from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.movies.models import (
    ActorModel,
    CountryModel,
    GenreModel,
    LanguageModel,
    MovieModel,
    MovieStatusEnum,
)


class MovieRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_movies(
            self,
            page: int,
            per_page: int,
            q: str | None = None,
            genre: str | None = None,
            country: str | None = None,
            movie_status: MovieStatusEnum | None = None,
    ) -> tuple[list[MovieModel], int]:
        query = select(MovieModel).where(
            MovieModel.deleted_at.is_(None)
        )

        if q:
            query = query.where(
                MovieModel.name.icontains(q, autoescape=True)
            )

        if genre:
            query = (
                query.join(MovieModel.genres)
                .where(func.lower(GenreModel.name) == genre.lower())
            )
        if country:
            query = (
                query.join(MovieModel.country)
                .where(func.lower(CountryModel.code) == country.lower())
            )
        if movie_status is not None:
            query = query.where(MovieModel.status == movie_status)

        total_items = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )

        statement = (
            query
            .order_by(MovieModel.date.desc(), MovieModel.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all()), total_items or 0

    async def get_by_id(self, movie_id: UUID) -> MovieModel | None:
        statement = (
            select(MovieModel)
            .options(
                selectinload(MovieModel.country),
                selectinload(MovieModel.genres),
                selectinload(MovieModel.actors),
                selectinload(MovieModel.languages),
            )
            .where(
                MovieModel.id == movie_id,
                MovieModel.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_or_create_country(self, code: str) -> CountryModel:
        result = await self.db.execute(
            select(CountryModel).where(
                func.lower(CountryModel.code) == code.lower()
            )
        )
        country = result.scalar_one_or_none()
        if country is not None:
            return country

        country = CountryModel(code=code)
        self.db.add(country)
        await self.db.flush()
        return country

    async def get_or_create_genre(self, name: str) -> GenreModel:
        result = await self.db.execute(
            select(GenreModel).where(
                func.lower(GenreModel.name) == name.lower()
            )
        )
        genre = result.scalar_one_or_none()
        if genre is not None:
            return genre

        genre = GenreModel(name=name)
        self.db.add(genre)
        await self.db.flush()
        return genre

    async def get_or_create_language(self, name: str) -> LanguageModel:
        result = await self.db.execute(
            select(LanguageModel).where(
                func.lower(LanguageModel.name) == name.lower()
            )
        )
        language = result.scalar_one_or_none()
        if language is not None:
            return language

        language = LanguageModel(name=name)
        self.db.add(language)
        await self.db.flush()
        return language

    async def get_actor_by_id(self, actor_id: UUID) -> ActorModel | None:
        return await self.db.get(ActorModel, actor_id)

    async def find_actors_by_name(self, name: str) -> list[ActorModel]:
        result = await self.db.execute(
            select(ActorModel)
            .where(func.lower(ActorModel.name) == name.lower())
            .limit(2)
        )
        return list(result.scalars().all())

    async def create_actor(self, name: str) -> ActorModel:
        actor = ActorModel(name=name)
        self.db.add(actor)
        await self.db.flush()
        return actor

    async def add_movie(self, movie: MovieModel) -> MovieModel:
        self.db.add(movie)
        await self.db.flush()
        return movie

    async def update_movie(
        self,
        movie: MovieModel,
        changes: dict[str, object],
    ) -> MovieModel:
        for field_name, value in changes.items():
            setattr(movie, field_name, value)

        await self.db.flush()
        return movie

    async def mark_deleted(
        self,
        movie: MovieModel,
        deleted_at: datetime,
    ) -> None:
        movie.deleted_at = deleted_at
        await self.db.flush()
