from uuid import UUID, uuid4
from pathlib import Path

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory
from app.movies.importer import collect_reference_names, pending_movie_rows
from app.movies.models import (
    ActorModel,
    CountryModel,
    GenreModel,
    LanguageModel,
    MovieModel,
    movies_actors,
    movies_genres,
    movies_languages,
)
from app.movies.validators import normalize_genre_name

ReferenceModel = (
    type[ActorModel] | type[CountryModel] | type[GenreModel] | type[LanguageModel]
)


async def ensure_reference_ids(
    db: AsyncSession,
    model: ReferenceModel,
    field_name: str,
    names: dict[str, str],
) -> dict[str, UUID]:
    column = getattr(model, field_name)
    result = await db.execute(select(model.id, column))

    ids: dict[str, UUID] = {}
    for record_id, value in result:
        key = value.lower()
        if key in names:
            if key in ids and ids[key] != record_id:
                raise ValueError(
                    f"Multiple {model.__tablename__} records named {value!r}"
                )
            ids[key] = record_id

    missing = [(key, value) for key, value in names.items() if key not in ids]

    for start in range(0, len(missing), 1000):
        batch = missing[start : start + 1000]
        rows = []

        for key, value in batch:
            record_id = uuid4()
            rows.append({"id": record_id, field_name: value})
            ids[key] = record_id

        await db.execute(insert(model), rows)

    return ids


async def import_full_catalog(path: Path) -> tuple[int, int]:
    movies, skipped = await pending_movie_rows(path)
    if not movies:
        return 0, skipped

    country_names, genre_names, actor_names, language_names = collect_reference_names(
        movies
    )

    async with async_session_factory() as db:
        async with db.begin():
            countries = await ensure_reference_ids(
                db, CountryModel, "code", country_names
            )
            genres = await ensure_reference_ids(db, GenreModel, "name", genre_names)
            actors = await ensure_reference_ids(db, ActorModel, "name", actor_names)
            languages = await ensure_reference_ids(
                db, LanguageModel, "name", language_names
            )

            movie_rows = []
            genre_links = []
            actor_links = []
            language_links = []

            for movie in movies:
                movie_id = uuid4()
                row = movie.model_dump(
                    exclude={"country", "genres", "actors", "languages"}
                )
                row.update(
                    {
                        "id": movie_id,
                        "country_id": countries[movie.country.lower()],
                    }
                )
                movie_rows.append(row)

                for name in {
                    normalize_genre_name(value).lower() for value in movie.genres
                }:
                    genre_links.append(
                        {
                            "movie_id": movie_id,
                            "genre_id": genres[name],
                        }
                    )

                movie_actor_ids = set()

                for reference in movie.actors:
                    if reference.name is None:
                        raise ValueError("CSV actor must have a name")

                    actor_id = actors[reference.name.lower()]
                    if actor_id in movie_actor_ids:
                        continue

                    movie_actor_ids.add(actor_id)
                    actor_links.append(
                        {
                            "movie_id": movie_id,
                            "actor_id": actor_id,
                        }
                    )

                for name in {value.lower() for value in movie.languages}:
                    language_links.append(
                        {
                            "movie_id": movie_id,
                            "language_id": languages[name],
                        }
                    )

            for table, rows in (
                (MovieModel, movie_rows),
                (movies_genres, genre_links),
                (movies_actors, actor_links),
                (movies_languages, language_links),
            ):
                for start in range(0, len(rows), 1000):
                    await db.execute(
                        insert(table),
                        rows[start : start + 1000],
                    )

    return len(movies), skipped
