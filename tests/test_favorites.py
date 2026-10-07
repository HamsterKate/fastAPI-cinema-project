from uuid import uuid4

from fastapi.testclient import TestClient


def create_test_movie(
    client: TestClient,
    moderator_headers: dict[str, str],
) -> str:
    suffix = uuid4().hex

    response = client.post(
        "/api/v2/movies",
        headers=moderator_headers,
        json={
            "name": f"Favorite movie {suffix}",
            "date": "2025-01-01",
            "score": 85,
            "overview": "A movie used by favorites tests.",
            "status": "Released",
            "budget": "100.00",
            "revenue": "250.00",
            "price": "9.99",
            "country": "UA",
            "genres": ["Drama"],
            "actors": [{"name": f"Favorite actor {suffix}"}],
            "languages": ["English"],
        },
    )

    assert response.status_code == 201

    return response.json()["movie"]["id"]


def test_user_can_add_list_and_remove_favorite(
    client: TestClient,
    active_user: dict[str, str],
    moderator_headers: dict[str, str],
) -> None:
    headers = {
        "Authorization": (
            f"Bearer {active_user['access_token']}"
        )
    }
    movie_id = create_test_movie(client, moderator_headers)

    empty_list_response = client.get(
        "/api/v2/favorites",
        headers=headers,
    )

    assert empty_list_response.status_code == 200
    assert empty_list_response.json()["total_items"] == 0

    add_response = client.post(
        f"/api/v2/favorites/{movie_id}",
        headers=headers,
    )

    assert add_response.status_code == 201
    assert add_response.json() == {
        "message": "Movie added to favorites"
    }

    duplicate_response = client.post(
        f"/api/v2/favorites/{movie_id}",
        headers=headers,
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == (
        "Movie is already in favorites"
    )

    list_response = client.get(
        "/api/v2/favorites",
        headers=headers,
    )

    assert list_response.status_code == 200
    assert list_response.json()["total_items"] == 1
    assert list_response.json()["movies"][0]["id"] == movie_id

    remove_response = client.delete(
        f"/api/v2/favorites/{movie_id}",
        headers=headers,
    )

    assert remove_response.status_code == 204

    final_list_response = client.get(
        "/api/v2/favorites",
        headers=headers,
    )

    assert final_list_response.status_code == 200
    assert final_list_response.json()["total_items"] == 0


def test_favorites_reject_missing_movie(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    response = client.post(
        f"/api/v2/favorites/{uuid4()}",
        headers={
            "Authorization": (
                f"Bearer {active_user['access_token']}"
            )
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_favorites_require_access_token(
    client: TestClient,
) -> None:
    response = client.get("/api/v2/favorites")

    assert response.status_code == 401


def test_remove_missing_favorite_returns_not_found(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    response = client.delete(
        f"/api/v2/favorites/{uuid4()}",
        headers={
            "Authorization": (
                f"Bearer {active_user['access_token']}"
            )
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Favorite not found"


