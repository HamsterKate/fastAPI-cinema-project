import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.profiles.schemas import ProfileUpdateRequestSchema


def test_profile_update_schema_normalizes_text_fields() -> None:
    profile_data = ProfileUpdateRequestSchema(
        first_name="  Kate  ",
        last_name="  Po  ",
        info="  Cinema lover  ",
    )

    assert profile_data.first_name == "Kate"
    assert profile_data.last_name == "Po"
    assert profile_data.info == "Cinema lover"


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"first_name": "   "},
        {"last_name": "   "},
        {"info": "   "},
    ],
)
def test_profile_update_schema_rejects_empty_changes(
    data: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequestSchema(**data)


def test_get_profile_returns_not_found_before_first_update(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    response = client.get(
        "/api/v2/profiles/me",
        headers={
            "Authorization": (
                f"Bearer {active_user['access_token']}"
            )
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"


def test_update_profile_creates_profile(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    headers = {
        "Authorization": (
            f"Bearer {active_user['access_token']}"
        )
    }

    update_response = client.patch(
        "/api/v2/profiles/me",
        headers=headers,
        json={
            "first_name": "Kate",
            "last_name": "Po",
            "gender": "woman",
            "date_of_birth": "2000-01-01",
            "info": "Cinema lover",
        },
    )

    assert update_response.status_code == 200

    data = update_response.json()
    assert data["user_id"]
    assert data["first_name"] == "Kate"
    assert data["last_name"] == "Po"
    assert data["gender"] == "woman"
    assert data["date_of_birth"] == "2000-01-01"
    assert data["info"] == "Cinema lover"
    assert data["avatar"] is None

    get_response = client.get(
        "/api/v2/profiles/me",
        headers=headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == data["id"]


def test_update_profile_modifies_existing_profile(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    headers = {
        "Authorization": (
            f"Bearer {active_user['access_token']}"
        )
    }

    first_response = client.patch(
        "/api/v2/profiles/me",
        headers=headers,
        json={
            "first_name": "Kate",
            "info": "First profile info",
        },
    )
    assert first_response.status_code == 200

    second_response = client.patch(
        "/api/v2/profiles/me",
        headers=headers,
        json={"info": "Updated profile info"},
    )

    assert second_response.status_code == 200

    data = second_response.json()
    assert data["first_name"] == "Kate"
    assert data["info"] == "Updated profile info"


def test_profile_endpoints_require_access_token(
    client: TestClient,
) -> None:
    response = client.get("/api/v2/profiles/me")

    assert response.status_code == 401


def test_upload_and_delete_avatar(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    headers = {
        "Authorization": (
            f"Bearer {active_user['access_token']}"
        )
    }

    create_profile_response = client.patch(
        "/api/v2/profiles/me",
        headers=headers,
        json={"first_name": "Kate"},
    )
    assert create_profile_response.status_code == 200

    upload_response = client.post(
        "/api/v2/profiles/me/avatar",
        headers=headers,
        files={
            "avatar": (
                "avatar.png",
                b"test image content",
                "image/png",
            )
        },
    )

    assert upload_response.status_code == 200
    assert upload_response.json()["avatar"] is not None

    delete_response = client.delete(
        "/api/v2/profiles/me/avatar",
        headers=headers,
    )

    assert delete_response.status_code == 204

    profile_response = client.get(
        "/api/v2/profiles/me",
        headers=headers,
    )

    assert profile_response.status_code == 200
    assert profile_response.json()["avatar"] is None


def test_upload_avatar_rejects_invalid_content_type(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    headers = {
        "Authorization": (
            f"Bearer {active_user['access_token']}"
        )
    }

    create_profile_response = client.patch(
        "/api/v2/profiles/me",
        headers=headers,
        json={"first_name": "Kate"},
    )
    assert create_profile_response.status_code == 200

    response = client.post(
        "/api/v2/profiles/me/avatar",
        headers=headers,
        files={
            "avatar": (
                "avatar.txt",
                b"not an image",
                "text/plain",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Avatar must be a JPEG or PNG image"
    )


def test_upload_avatar_rejects_file_larger_than_one_mb(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    headers = {
        "Authorization": (
            f"Bearer {active_user['access_token']}"
        )
    }

    create_profile_response = client.patch(
        "/api/v2/profiles/me",
        headers=headers,
        json={"first_name": "Kate"},
    )
    assert create_profile_response.status_code == 200

    response = client.post(
        "/api/v2/profiles/me/avatar",
        headers=headers,
        files={
            "avatar": (
                "large.png",
                b"x" * (1024 * 1024 + 1),
                "image/png",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Avatar size must not exceed 1 MB"
    )


