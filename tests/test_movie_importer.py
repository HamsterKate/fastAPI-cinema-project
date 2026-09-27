from datetime import date
from decimal import Decimal

import pytest
import csv
from pathlib import Path
from uuid import uuid4

from app.movies.bulk_importer import ensure_reference_ids
from app.movies.models import GenreModel
from app.movies.importer import collect_reference_names
from app.movies.schemas import MovieCreateRequestSchema
from app.movies.price_generator import add_prices, calculate_price


@pytest.mark.parametrize(
    ("release_date", "score", "revenue", "expected_price"),
    [
        (
            date(date.today().year, 1, 1),
            Decimal("7.0"),
            Decimal("0"),
            Decimal("6.99"),
        ),
        (
            date(date.today().year - 3, 1, 1),
            Decimal("7.0"),
            Decimal("100000000"),
            Decimal("6.99"),
        ),
        (
            date(date.today().year - 10, 1, 1),
            Decimal("8.0"),
            Decimal("500000000"),
            Decimal("7.99"),
        ),
        (
            date(date.today().year, 1, 1),
            Decimal("9.5"),
            Decimal("1000000000"),
            Decimal("9.99"),
        ),
    ],
)
def test_calculate_movie_price(
    release_date: date,
    score: Decimal,
    revenue: Decimal,
    expected_price: Decimal,
) -> None:
    assert calculate_price(
        release_date,
        score,
        revenue,
    ) == expected_price


def test_add_prices_writes_price_column(
    tmp_path: Path,
) -> None:
    path = tmp_path / "movies.csv"
    path.write_text(
        "names,date_x,score,revenue\n"
        "Classic movie,2000-01-01,7.0,0\n",
        encoding="utf-8",
    )

    total = add_prices(path)

    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert total == 1
    assert rows == [
        {
            "names": "Classic movie",
            "date_x": "2000-01-01",
            "score": "7.0",
            "revenue": "0",
            "price": "4.99",
        },
    ]


def test_add_prices_replaces_existing_price_column(
    tmp_path: Path,
) -> None:
    path = tmp_path / "movies.csv"
    path.write_text(
        "names,date_x,score,revenue,price\n"
        "Popular movie,2000-01-01,8.0,500000000,1.00\n",
        encoding="utf-8",
    )

    add_prices(path)

    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows[0]["price"] == "7.99"
    assert list(rows[0]) == [
        "names",
        "date_x",
        "score",
        "revenue",
        "price",
    ]


def test_collect_reference_names_normalizes_and_deduplicates() -> None:
    first_movie = MovieCreateRequestSchema(
        name="First movie",
        date="2020-01-01",
        score=80,
        overview="First overview",
        status="Released",
        budget="100.00",
        revenue="200.00",
        price="4.99",
        country="us",
        genres=[" science - fiction ", "Drama"],
        actors=[{"name": "Kate"}, {"name": "John"}],
        languages=["English", "Ukrainian"],
    )
    second_movie = MovieCreateRequestSchema(
        name="Second movie",
        date="2021-01-01",
        score=70,
        overview="Second overview",
        status="Released",
        budget="100.00",
        revenue="200.00",
        price="4.99",
        country="US",
        genres=["Science-Fiction", "drama"],
        actors=[{"name": "kate"}],
        languages=["english"],
    )

    countries, genres, actors, languages = collect_reference_names(
        [first_movie, second_movie],
    )

    assert countries == {"us": "US"}
    assert genres == {
        "science-fiction": "Science-Fiction",
        "drama": "Drama",
    }
    assert actors == {
        "kate": "Kate",
        "john": "John",
    }
    assert languages == {
        "english": "English",
        "ukrainian": "Ukrainian",
    }


@pytest.mark.asyncio
async def test_ensure_reference_ids_reuses_existing_and_adds_missing() -> None:
    existing_id = uuid4()

    class FakeResult:
        def __iter__(self):
            return iter([(existing_id, "Drama")])

    class FakeDatabase:
        def __init__(self) -> None:
            self.calls: list[object] = []

        async def execute(
            self,
            statement: object,
            params: object = None,
        ) -> object:
            self.calls.append((statement, params))

            if len(self.calls) == 1:
                return FakeResult()

            return None

    db = FakeDatabase()

    ids = await ensure_reference_ids(
        db,
        GenreModel,
        "name",
        {
            "drama": "Drama",
            "comedy": "Comedy",
        },
    )

    assert ids["drama"] == existing_id
    assert "comedy" in ids
    assert len(db.calls) == 2

    inserted_rows = db.calls[1][1]
    assert inserted_rows == [
        {
            "id": ids["comedy"],
            "name": "Comedy",
        },
    ]


@pytest.mark.asyncio
async def test_ensure_reference_ids_rejects_duplicate_reference_records() -> None:
    class FakeResult:
        def __iter__(self):
            return iter(
                [
                    (uuid4(), "Drama"),
                    (uuid4(), "DRAMA"),
                ],
            )

    class FakeDatabase:
        async def execute(
            self,
            statement: object,
            params: object = None,
        ) -> object:
            return FakeResult()

    with pytest.raises(
        ValueError,
        match="Multiple genres records named",
    ):
        await ensure_reference_ids(
            FakeDatabase(),
            GenreModel,
            "name",
            {"drama": "Drama"},
        )
