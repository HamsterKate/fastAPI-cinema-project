import re
from email import policy
from email import message_from_string
from urllib.parse import unquote

import httpx

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid4().hex}@example.com"


def get_activation_token(recipient: str) -> str:
    response = httpx.get(
        "http://mailhog:8025/api/v2/messages",
        timeout=5,
    )
    response.raise_for_status()

    for item in response.json()["items"]:
        recipients = item["Content"]["Headers"].get("To", [])

        if recipient not in recipients:
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
        f"Activation email for {recipient} was not found."
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
