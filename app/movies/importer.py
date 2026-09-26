import csv
from pathlib import Path

from sqlalchemy import func, select

from app.db.database import async_session_factory
from app.movies.models import MovieModel
from app.movies.services import create_movie
from app.movies.schemas import MovieCreateRequestSchema
from app.movies.validators import normalize_genre_name


def load_movie_rows(path: Path) -> list[MovieCreateRequestSchema]:
    movies = []

    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            movies.append(
                MovieCreateRequestSchema.model_validate(
                    {
                        "name": row["names"],
                        "date": row["date_x"],
                        "score": row["score"],
                        "overview": row["overview"],
                        "status": row["status"],
                        "budget": row["budget_x"],
                        "revenue": row["revenue"],
                        "country": row["country"],
                        "genres": row["genre"].split(","),
                        "actors": [
                            {"name": name.strip()}
                            for name in row["crew"].split(",")
                            if name.strip()
                        ],
                        "languages": row["orig_lang"].split(","),
                    }
                )
            )

    return movies


async def import_movies(path: Path) -> tuple[int, int]:
    movies = load_movie_rows(path)
    imported = 0
    skipped = 0

    async with async_session_factory() as db:
        for data in movies:
            existing_id = await db.scalar(
                select(MovieModel.id)
                .where(
                    func.lower(MovieModel.name) == data.name.lower(),
                    MovieModel.date == data.date,
                )
                .limit(1)
            )

            if existing_id is not None:
                skipped += 1
                continue

            await create_movie(db, data)
            imported += 1

    return imported, skipped


async def pending_movie_rows(
    path: Path,
) -> tuple[list[MovieCreateRequestSchema], int]:
    movies = load_movie_rows(path)

    async with async_session_factory() as db:
        result = await db.execute(
            select(func.lower(MovieModel.name), MovieModel.date)
        )
        seen = set(result.all())

    pending = []

    for movie in movies:
        key = (movie.name.lower(), movie.date)
        if key in seen:
            continue

        seen.add(key)
        pending.append(movie)

    return pending, len(movies) - len(pending)


def collect_reference_names(
    movies: list[MovieCreateRequestSchema],
) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    countries = {}
    genres = {}
    actors = {}
    languages = {}

    for movie in movies:
        countries.setdefault(movie.country.lower(), movie.country)

        for raw_name in movie.genres:
            name = normalize_genre_name(raw_name)
            genres.setdefault(name.lower(), name)

        for actor in movie.actors:
            if actor.name is not None:
                actors.setdefault(actor.name.lower(), actor.name)

        for name in movie.languages:
            languages.setdefault(name.lower(), name)

    return countries, genres, actors, languages
