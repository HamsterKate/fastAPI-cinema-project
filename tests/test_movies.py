import pytest

from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.movies.schemas import (
    ActorReferenceSchema,
    MovieCreateRequestSchema,
    MovieUpdateRequestSchema,
)
from app.core.pagination import build_pagination_links
from app.movies.validators import (
    is_valid_country_code,
    normalize_country_code,
    normalize_genre_name,
)


@pytest.mark.parametrize(
    ("raw_country", "expected_country"),
    [
        ("ua", "UA"),
        (" Us ", "US"),
        ("gbr", "GBR"),
    ],
)
def test_normalize_country_code(
    raw_country: str,
    expected_country: str,
) -> None:
    assert normalize_country_code(raw_country) == expected_country


@pytest.mark.parametrize(
    "country_code",
    [
        "",
        "U",
        "UKRA",
        "12",
        "U1",
    ],
)
def test_is_valid_country_code_rejects_invalid_values(
    country_code: str,
) -> None:
    assert is_valid_country_code(country_code) is False


def test_build_pagination_links_preserves_filters() -> None:
    previous_page, next_page, total_pages = build_pagination_links(
        path="/api/v2/movies",
        page=2,
        per_page=10,
        total_items=21,
        query_params={
            "q": "star wars",
            "country": "UA",
        },
    )

    assert previous_page == (
        "/api/v2/movies?page=1&per_page=10&q=star+wars&country=UA"
    )
    assert next_page == (
        "/api/v2/movies?page=3&per_page=10&q=star+wars&country=UA"
    )
    assert total_pages == 3


def test_movie_create_schema_normalizes_input() -> None:
    movie_data = MovieCreateRequestSchema(
        name="  Example movie  ",
        date=date(2025, 1, 1),
        score=85,
        overview="  An example overview.  ",
        status="Released",
        budget="100.00",
        revenue="250.00",
        price="9.99",
        country=" ua ",
        genres=["  Drama  "],
        actors=[{"name": "  Jane Doe  "}],
        languages=["  English  "],
    )

    assert movie_data.name == "Example movie"
    assert movie_data.overview == "An example overview."
    assert movie_data.country == "UA"
    assert movie_data.genres == ["Drama"]
    assert movie_data.actors[0].name == "Jane Doe"
    assert movie_data.languages == ["English"]


def test_actor_reference_requires_exactly_one_identifier() -> None:
    with pytest.raises(ValidationError):
        ActorReferenceSchema()

    with pytest.raises(ValidationError):
        ActorReferenceSchema(
            id=uuid4(),
            name="Jane Doe",
        )


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"name": None},
    ],
)
def test_movie_update_schema_requires_real_changes(
    data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        MovieUpdateRequestSchema(**data)


def test_list_movies_returns_paginated_response(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v2/movies",
        params={
            "page": 1,
            "per_page": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert set(data) == {
        "movies",
        "prev_page",
        "next_page",
        "total_pages",
        "total_items",
    }
    assert len(data["movies"]) <= 2
    assert data["prev_page"] is None


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"per_page": 21},
    ],
)
def test_list_movies_rejects_invalid_pagination(
    client: TestClient,
    params: dict[str, int],
) -> None:
    response = client.get(
        "/api/v2/movies",
        params=params,
    )

    assert response.status_code == 422


def test_list_movies_rejects_invalid_country_code(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v2/movies",
        params={"country": "U1"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Country code must contain 2 or 3 Latin letters"
    )


def test_get_movie_detail_returns_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        f"/api/v2/movies/{uuid4()}",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_create_movie_requires_moderator_or_admin(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    response = client.post(
        "/api/v2/movies",
        headers={
            "Authorization": (
                f"Bearer {active_user['access_token']}"
            )
        },
        json={
            "name": "Test movie",
            "date": "2025-01-01",
            "score": 85,
            "overview": "A test movie overview.",
            "status": "Released",
            "budget": "100.00",
            "revenue": "250.00",
            "price": "9.99",
            "country": "UA",
            "genres": ["Drama"],
            "actors": [{"name": "Test actor"}],
            "languages": ["English"],
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("raw_genre", "expected_genre"),
    [
        ("  science   fiction  ", "Science Fiction"),
        ("sci - fi", "Sci-Fi"),
    ],
)
def test_normalize_genre_name(
    raw_genre: str,
    expected_genre: str,
) -> None:
    assert normalize_genre_name(raw_genre) == expected_genre


