from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import get_activation_token


def test_user_can_get_empty_orders_list(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }

    response = client.get("/api/v2/orders", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "orders": [],
        "prev_page": None,
        "next_page": None,
        "total_pages": 0,
        "total_items": 0,
    }


def test_checkout_rejects_empty_cart(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }

    response = client.post("/api/v2/orders/checkout", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Cart is empty"


def test_orders_require_access_token(client: TestClient) -> None:
    other_user_email = f"other-user-{uuid4().hex}@example.com"
    response = client.get("/api/v2/orders")

    assert response.status_code == 401


def create_test_movie(
    client: TestClient,
    moderator_headers: dict[str, str],
) -> str:
    suffix = uuid4().hex

    response = client.post(
        "/api/v2/movies",
        headers=moderator_headers,
        json={
            "name": f"Order movie {suffix}",
            "date": "2025-01-01",
            "score": 85,
            "overview": "A movie used by order tests.",
            "status": "Released",
            "budget": "100.00",
            "revenue": "250.00",
            "price": "9.99",
            "country": "UA",
            "genres": ["Drama"],
            "actors": [{"name": f"Order actor {suffix}"}],
            "languages": ["English"],
        },
    )

    assert response.status_code == 201

    return response.json()["movie"]["id"]


def create_pending_order(
    client: TestClient,
    active_user: dict[str, str],
    moderator_headers: dict[str, str],
) -> dict:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }
    movie_id = create_test_movie(client, moderator_headers)

    add_to_cart_response = client.post(
        f"/api/v2/cart/items/{movie_id}",
        headers=headers,
    )
    assert add_to_cart_response.status_code == 201

    checkout_response = client.post(
        "/api/v2/orders/checkout",
        headers=headers,
    )
    assert checkout_response.status_code == 201

    return checkout_response.json()


def test_checkout_creates_pending_order_and_clears_cart(
    client: TestClient,
    active_user: dict[str, str],
    moderator_headers: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }
    movie_id = create_test_movie(client, moderator_headers)

    add_to_cart_response = client.post(
        f"/api/v2/cart/items/{movie_id}",
        headers=headers,
    )
    assert add_to_cart_response.status_code == 201

    checkout_response = client.post(
        "/api/v2/orders/checkout",
        headers=headers,
    )

    assert checkout_response.status_code == 201

    order = checkout_response.json()
    assert order["status"] == "pending"
    assert order["total_price"] == "9.99"
    assert len(order["items"]) == 1
    assert order["items"][0]["movie_id"] == movie_id
    assert order["items"][0]["unit_price"] == "9.99"

    cart_response = client.get("/api/v2/cart", headers=headers)

    assert cart_response.status_code == 200
    assert cart_response.json()["total_items"] == 0


def test_user_can_get_own_order(
    client: TestClient,
    active_user: dict[str, str],
    moderator_headers: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }
    created_order = create_pending_order(
        client,
        active_user,
        moderator_headers,
    )

    response = client.get(
        f"/api/v2/orders/{created_order['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_order["id"]
    assert response.json()["status"] == "pending"


def test_user_can_cancel_pending_order(
    client: TestClient,
    active_user: dict[str, str],
    moderator_headers: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }
    created_order = create_pending_order(
        client,
        active_user,
        moderator_headers,
    )

    response = client.post(
        f"/api/v2/orders/{created_order['id']}/cancel",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_order["id"]
    assert response.json()["status"] == "canceled"


def test_get_missing_order_returns_not_found(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }

    response = client.get(
        f"/api/v2/orders/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_cannot_cancel_order_twice(
    client: TestClient,
    active_user: dict[str, str],
    moderator_headers: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }
    created_order = create_pending_order(
        client,
        active_user,
        moderator_headers,
    )

    first_response = client.post(
        f"/api/v2/orders/{created_order['id']}/cancel",
        headers=headers,
    )
    assert first_response.status_code == 200

    second_response = client.post(
        f"/api/v2/orders/{created_order['id']}/cancel",
        headers=headers,
    )

    assert second_response.status_code == 409
    assert (
        second_response.json()["detail"]
        == "Only pending orders can be canceled"
    )


def test_user_cannot_get_another_users_order(
    client: TestClient,
    active_user: dict[str, str],
    moderator_headers: dict[str, str],
) -> None:
    other_user_email = f"other-user-{uuid4().hex}@example.com"

    created_order = create_pending_order(
        client,
        active_user,
        moderator_headers,
    )

    registration_response = client.post(
        "/api/v2/accounts/register",
        json={
            "email": other_user_email,
            "password": "StrongPassword1!",
        },
    )
    assert registration_response.status_code == 201

    activation_token = get_activation_token(other_user_email)
    activation_response = client.get(
        "/api/v2/accounts/activate",
        params={"token": activation_token},
    )
    assert activation_response.status_code == 200

    login_response = client.post(
        "/api/v2/accounts/login",
        json={
            "email": other_user_email,
            "password": "StrongPassword1!",
        },
    )
    assert login_response.status_code == 200

    other_user_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        ),
    }

    response = client.get(
        f"/api/v2/orders/{created_order['id']}",
        headers=other_user_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_orders_list_contains_created_order(
    client: TestClient,
    active_user: dict[str, str],
    moderator_headers: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }
    created_order = create_pending_order(
        client,
        active_user,
        moderator_headers,
    )

    response = client.get("/api/v2/orders", headers=headers)

    assert response.status_code == 200

    body = response.json()
    assert body["total_items"] == 1
    assert body["total_pages"] == 1
    assert body["orders"][0]["id"] == created_order["id"]
    assert body["orders"][0]["status"] == "pending"


def test_checkout_rejects_movie_with_pending_order(
    client: TestClient,
    active_user: dict[str, str],
    moderator_headers: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }
    movie_id = create_test_movie(client, moderator_headers)

    first_add_response = client.post(
        f"/api/v2/cart/items/{movie_id}",
        headers=headers,
    )
    assert first_add_response.status_code == 201

    first_checkout_response = client.post(
        "/api/v2/orders/checkout",
        headers=headers,
    )
    assert first_checkout_response.status_code == 201

    second_add_response = client.post(
        f"/api/v2/cart/items/{movie_id}",
        headers=headers,
    )
    assert second_add_response.status_code == 201

    second_checkout_response = client.post(
        "/api/v2/orders/checkout",
        headers=headers,
    )

    assert second_checkout_response.status_code == 409
    assert (
        second_checkout_response.json()["detail"]
        == "One or more movies already have a pending order"
    )
