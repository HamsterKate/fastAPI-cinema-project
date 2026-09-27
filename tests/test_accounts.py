import pytest

from uuid import uuid4

from fastapi.testclient import TestClient

from app.accounts.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.accounts.schemas import UserRegistrationSchema
from app.accounts.security import hash_password, verify_password
from app.accounts.tokens import generate_token, hash_token
from pydantic import ValidationError
from tests.conftest import get_activation_token


@pytest.mark.parametrize(
    ("email", "expected_email"),
    [
        ("Kate@Example.COM", "kate@example.com"),
        ("USER@Example.org", "user@example.org"),
    ],
)
def test_user_registration_schema_normalizes_email(
    email: str,
    expected_email: str,
) -> None:
    user_data = UserRegistrationSchema(
        email=email,
        password="StrongPassword1!",
    )

    assert str(user_data.email) == expected_email


@pytest.mark.parametrize(
    "password",
    [
        "Short1!",
        "lowercase1!",
        "UPPERCASE1!",
        "NoDigits!",
        "NoSpecial1",
    ],
)
def test_user_registration_schema_rejects_weak_password(
    password: str,
) -> None:
    with pytest.raises(ValidationError):
        UserRegistrationSchema(
            email="user@example.com",
            password=password,
        )


@pytest.mark.parametrize(
    "email",
    [
        "not-an-email",
        "user@",
        "user@localhost",
    ],
)
def test_user_registration_schema_rejects_invalid_email(
    email: str,
) -> None:
    with pytest.raises(ValidationError):
        UserRegistrationSchema(
            email=email,
            password="StrongPassword1!",
        )


def test_password_hash_can_be_verified() -> None:
    password = "StrongPassword1!"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password) is True
    assert verify_password("AnotherPassword1!", hashed_password) is False


def test_generated_token_is_hashed_before_storage() -> None:
    token = generate_token()

    token_hash = hash_token(token)

    assert token
    assert token_hash != token
    assert token_hash == hash_token(token)


def test_jwt_tokens_contain_expected_data() -> None:
    user_id = uuid4()

    access_payload = decode_token(
        create_access_token(user_id),
        expected_type="access",
    )
    refresh_payload = decode_token(
        create_refresh_token(user_id),
        expected_type="refresh",
    )

    assert access_payload["sub"] == str(user_id)
    assert access_payload["type"] == "access"

    assert refresh_payload["sub"] == str(user_id)
    assert refresh_payload["type"] == "refresh"
    assert refresh_payload["jti"]


def test_access_token_cannot_be_used_as_refresh_token() -> None:
    access_token = create_access_token(uuid4())

    with pytest.raises(ValueError, match="Invalid token type"):
        decode_token(
            access_token,
            expected_type="refresh",
        )


def test_register_creates_inactive_user(
    client: TestClient,
    unique_email: str,
) -> None:
    response = client.post(
        "/api/v2/accounts/register",
        json={
            "email": unique_email,
            "password": "StrongPassword1!",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["email"] == unique_email
    assert data["is_active"] is False
    assert data["is_verified"] is False
    assert data["id"]
    assert data["group_id"]


def test_register_rejects_duplicate_email(
    client: TestClient,
    unique_email: str,
) -> None:
    payload = {
        "email": unique_email,
        "password": "StrongPassword1!",
    }

    first_response = client.post(
        "/api/v2/accounts/register",
        json=payload,
    )
    second_response = client.post(
        "/api/v2/accounts/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_activate_rejects_invalid_token(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v2/accounts/activate",
        params={"token": "invalid-token"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid activation token."


def test_activate_user_from_activation_email(
    client: TestClient,
    unique_email: str,
) -> None:
    registration_response = client.post(
        "/api/v2/accounts/register",
        json={
            "email": unique_email,
            "password": "StrongPassword1!",
        },
    )

    assert registration_response.status_code == 201

    token = get_activation_token(unique_email)

    activation_response = client.get(
        "/api/v2/accounts/activate",
        params={"token": token},
    )

    assert activation_response.status_code == 200
    assert activation_response.json() == {
        "message": "Account activated successfully.",
    }
    repeated_activation_response = client.get(
        "/api/v2/accounts/activate",
        params={"token": token},
    )

    assert repeated_activation_response.status_code == 400
    assert repeated_activation_response.json()["detail"] == (
        "Invalid activation token."
    )


def test_login_returns_tokens_for_activated_user(
    client: TestClient,
    unique_email: str,
) -> None:
    password = "StrongPassword1!"

    registration_response = client.post(
        "/api/v2/accounts/register",
        json={
            "email": unique_email,
            "password": password,
        },
    )
    assert registration_response.status_code == 201

    token = get_activation_token(unique_email)

    activation_response = client.get(
        "/api/v2/accounts/activate",
        params={"token": token},
    )
    assert activation_response.status_code == 200

    login_response = client.post(
        "/api/v2/accounts/login",
        json={
            "email": unique_email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    data = login_response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


def test_login_rejects_inactive_user(
    client: TestClient,
    unique_email: str,
) -> None:
    password = "StrongPassword1!"

    registration_response = client.post(
        "/api/v2/accounts/register",
        json={
            "email": unique_email,
            "password": password,
        },
    )
    assert registration_response.status_code == 201

    login_response = client.post(
        "/api/v2/accounts/login",
        json={
            "email": unique_email,
            "password": password,
        },
    )

    assert login_response.status_code == 403
    assert login_response.json()["detail"] == "Account is not activated."


def test_get_my_profile_returns_authenticated_user(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    response = client.get(
        "/api/v2/accounts/me",
        headers={
            "Authorization": (
                f"Bearer {active_user['access_token']}"
            )
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["email"] == active_user["email"]
    assert data["is_active"] is True
    assert data["is_verified"] is True


def test_get_my_profile_rejects_missing_access_token(
    client: TestClient,
) -> None:
    response = client.get("/api/v2/accounts/me")

    assert response.status_code == 401


def test_login_rejects_invalid_password(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    response = client.post(
        "/api/v2/accounts/login",
        json={
            "email": active_user["email"],
            "password": "WrongPassword1!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_refresh_rotates_refresh_token(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    old_refresh_token = active_user["refresh_token"]

    response = client.post(
        "/api/v2/accounts/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["refresh_token"] != old_refresh_token

    reused_token_response = client.post(
        "/api/v2/accounts/refresh",
        json={"refresh_token": old_refresh_token},
    )

    assert reused_token_response.status_code == 401
    assert reused_token_response.json()["detail"] == (
        "Refresh token has been revoked."
    )


def test_logout_revokes_refresh_token(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    refresh_token = active_user["refresh_token"]

    logout_response = client.post(
        "/api/v2/accounts/logout",
        json={"refresh_token": refresh_token},
    )

    assert logout_response.status_code == 204

    refresh_response = client.post(
        "/api/v2/accounts/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == (
        "Refresh token has been revoked."
    )

