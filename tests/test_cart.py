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
            "name": f"Cart movie {suffix}",
            "date": "2025-01-01",
            "score": 85,
            "overview": "A movie used by cart tests.",
            "status": "Released",
            "budget": "100.00",
            "revenue": "250.00",
            "price": "9.99",
            "country": "UA",
            "genres": ["Drama"],
            "actors": [{"name": f"Cart actor {suffix}"}],
            "languages": ["English"],
        },
    )

    assert response.status_code == 201

    return response.json()["movie"]["id"]


def test_user_can_add_duplicate_and_remove_cart_item(
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

    empty_cart_response = client.get(
        "/api/v2/cart",
        headers=headers,
    )

    assert empty_cart_response.status_code == 200
    assert empty_cart_response.json()["total_items"] == 0
    assert empty_cart_response.json()["total_price"] == "0.00"

    add_response = client.post(
        f"/api/v2/cart/items/{movie_id}",
        headers=headers,
    )

    assert add_response.status_code == 201
    assert add_response.json()["total_items"] == 1
    assert add_response.json()["total_price"] == "9.99"
    assert add_response.json()["items"][0]["movie"]["id"] == movie_id

    duplicate_response = client.post(
        f"/api/v2/cart/items/{movie_id}",
        headers=headers,
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == (
        "Movie is already in the cart"
    )

    remove_response = client.delete(
        f"/api/v2/cart/items/{movie_id}",
        headers=headers,
    )

    assert remove_response.status_code == 200
    assert remove_response.json()["total_items"] == 0


def test_clear_cart_removes_all_items(
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

    add_response = client.post(
        f"/api/v2/cart/items/{movie_id}",
        headers=headers,
    )
    assert add_response.status_code == 201

    clear_response = client.delete(
        "/api/v2/cart/items",
        headers=headers,
    )

    assert clear_response.status_code == 200
    assert clear_response.json()["total_items"] == 0
    assert clear_response.json()["total_price"] == "0.00"


def test_cart_rejects_missing_movie(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    response = client.post(
        f"/api/v2/cart/items/{uuid4()}",
        headers={
            "Authorization": (
                f"Bearer {active_user['access_token']}"
            )
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_cart_requires_access_token(
    client: TestClient,
) -> None:
    response = client.get("/api/v2/cart")

    assert response.status_code == 401


def test_remove_movie_not_in_cart_returns_not_found(
    client: TestClient,
    active_user: dict[str, str],
    moderator_headers: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }
    movie_id = create_test_movie(client, moderator_headers)

    response = client.delete(
        f"/api/v2/cart/items/{movie_id}",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie is not in the cart"
