import pytest

from uuid import uuid4

from app.accounts.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.accounts.schemas import UserRegistrationSchema
from app.accounts.security import hash_password, verify_password
from app.accounts.tokens import generate_token, hash_token
from pydantic import ValidationError


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