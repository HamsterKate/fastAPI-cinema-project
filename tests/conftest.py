import re
from collections.abc import Generator
from email import policy
from email.header import decode_header, make_header
from email import message_from_string
from urllib.parse import unquote
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.accounts.jwt import create_access_token
from app.accounts.models import (
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)
from app.accounts.security import hash_password
from app.db.database import async_session_factory
from main import app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid4().hex}@example.com"


def get_token_from_email(
    recipient: str,
    subject: str,
) -> str:
    response = httpx.get(
        "http://mailhog:8025/api/v2/messages",
        timeout=5,
    )
    response.raise_for_status()

    for item in response.json()["items"]:
        recipients = item["Content"]["Headers"].get("To", [])
        subjects = item["Content"]["Headers"].get("Subject", [])
        decoded_subjects = [
            str(make_header(decode_header(value)))
            for value in subjects
        ]

        if recipient not in recipients or subject not in decoded_subjects:
            continue

        message = message_from_string(
            item["Raw"]["Data"],
            policy=policy.default,
        )
        body = message.get_body(
            preferencelist=("plain",),
        ).get_content()

        match = re.search(r"[?&]token=([^\s]+)", body)

        if match:
            return unquote(match.group(1))

    raise AssertionError(
        f"Email with subject {subject!r} for {recipient} was not found."
    )


def get_activation_token(recipient: str) -> str:
    return get_token_from_email(
        recipient,
        "Cinema 2.0 — Activate your account",
    )


def get_password_reset_token(recipient: str) -> str:
    return get_token_from_email(
        recipient,
        "Cinema 2.0 — Reset your password",
    )


@pytest.fixture
def active_user(
    client: TestClient,
    unique_email: str,
) -> dict[str, str]:
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

    tokens = login_response.json()

    return {
        "email": unique_email,
        "password": password,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
    }


@pytest.fixture
def moderator_headers(
    client: TestClient,
) -> Generator[dict[str, str], None, None]:
    user_id = uuid4()
    email = f"moderator-{user_id.hex}@example.com"

    async def create_moderator() -> None:
        async with async_session_factory() as db:
            group = await db.scalar(
                select(UserGroupModel).where(
                    UserGroupModel.name == UserGroupEnum.MODERATOR
                )
            )
            assert group is not None

            db.add(
                UserModel(
                    id=user_id,
                    email=email,
                    hashed_password=hash_password(
                        "StrongPassword1!"
                    ),
                    is_active=True,
                    is_verified=True,
                    group_id=group.id,
                )
            )
            await db.commit()

    async def delete_moderator() -> None:
        async with async_session_factory() as db:
            await db.execute(
                delete(UserModel).where(UserModel.id == user_id)
            )
            await db.commit()

    client.portal.call(create_moderator)

    yield {
        "Authorization": (
            f"Bearer {create_access_token(user_id)}"
        )
    }

    client.portal.call(delete_moderator)