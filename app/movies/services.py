from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.movies.models import ActorModel, GenreModel, LanguageModel, MovieModel
from app.movies.validators import normalize_genre_name
from app.movies.repository import MovieRepository
from app.movies.schemas import (
    ActorReferenceSchema,
    MovieCreateRequestSchema,
    MovieListResponseSchema,
)


class ActorNotFoundError(Exception):
    def __init__(self, actor_id: str) -> None:
        self.actor_id = actor_id
        super().__init__(f"Actor {actor_id} was not found")


class AmbiguousActorError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            f"Multiple actors named '{name}' exist; provide an actor ID"
        )


async def resolve_actors(
    repository: MovieRepository,
    references: list[ActorReferenceSchema],
) -> list[ActorModel]:
    actors: list[ActorModel] = []
    seen_ids = set()

    for reference in references:
        if reference.id is not None:
            actor = await repository.get_actor_by_id(reference.id)
            if actor is None:
                raise ActorNotFoundError(str(reference.id))
        else:
            # ActorReferenceSchema guarantees a name when id is absent.
            assert reference.name is not None

            matches = await repository.find_actors_by_name(reference.name)
            if len(matches) > 1:
                raise AmbiguousActorError(reference.name)

            actor = (
                matches[0]
                if matches
                else await repository.create_actor(reference.name)
            )

        if actor.id not in seen_ids:
            actors.append(actor)
            seen_ids.add(actor.id)

    return actors


async def resolve_genres(
    repository: MovieRepository,
    names: list[str],
) -> tuple[list[GenreModel], list[str]]:
    genres: list[GenreModel] = []
    messages: list[str] = []
    seen_ids = set()

    for original_name in names:
        canonical_name = normalize_genre_name(original_name)
        genre = await repository.get_or_create_genre(canonical_name)

        if original_name != genre.name:
            message = (
                f"Genre '{original_name}' was saved as '{genre.name}'."
            )
            if message not in messages:
                messages.append(message)

        if genre.id not in seen_ids:
            genres.append(genre)
            seen_ids.add(genre.id)

    return genres, messages


async def resolve_languages(
    repository: MovieRepository,
    names: list[str],
) -> list[LanguageModel]:
    languages: list[LanguageModel] = []
    seen_ids = set()

    for name in names:
        language = await repository.get_or_create_language(name)

        if language.id not in seen_ids:
            languages.append(language)
            seen_ids.add(language.id)

    return languages


class CatalogConflictError(Exception):
    pass


async def create_movie(
    db: AsyncSession,
    data: MovieCreateRequestSchema,
) -> tuple[MovieModel, list[str]]:
    repository = MovieRepository(db)

    try:
        country = await repository.get_or_create_country(data.country)
        genres, messages = await resolve_genres(repository, data.genres)
        actors = await resolve_actors(repository, data.actors)
        languages = await resolve_languages(repository, data.languages)

        movie_fields = data.model_dump(
            exclude={"country", "genres", "actors", "languages"}
        )
        movie = MovieModel(
            **movie_fields,
            country=country,
            genres=genres,
            actors=actors,
            languages=languages,
        )

        await repository.add_movie(movie)
        await db.commit()

    except IntegrityError as exc:
        await db.rollback()
        raise CatalogConflictError(
            "Movie or related data conflicts with an existing record"
        ) from exc
    except Exception:
        await db.rollback()
        raise

    saved_movie = await repository.get_by_id(movie.id)
    assert saved_movie is not None

    return saved_movie, messages


async def get_movies_page(
    db: AsyncSession,
    page: int,
    per_page: int,
    path: str,
) -> MovieListResponseSchema:
    repository = MovieRepository(db)
    movies, total_items = await repository.list_movies(page, per_page)
    total_pages = (total_items + per_page - 1) // per_page

    prev_page = (
        f"{path}?page={page - 1}&per_page={per_page}"
        if page > 1
        else None
    )
    next_page = (
        f"{path}?page={page + 1}&per_page={per_page}"
        if page < total_pages
        else None
    )

    return MovieListResponseSchema(
        movies=movies,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items,
    )


async def get_movie_detail(
    db: AsyncSession,
    movie_id: UUID,
) -> MovieModel | None:
    repository = MovieRepository(db)
    return await repository.get_by_id(movie_id)
