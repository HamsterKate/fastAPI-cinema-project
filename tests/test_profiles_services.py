from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.profiles.services import get_profile, update_profile


@pytest.mark.asyncio
async def test_get_profile_returns_repository_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    profile = SimpleNamespace(user_id=user_id)

    class FakeProfileRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_user_id(
            self,
            current_user_id: object,
        ) -> object:
            return profile

    monkeypatch.setattr(
        "app.profiles.services.ProfileRepository",
        FakeProfileRepository,
    )

    assert await get_profile(SimpleNamespace(), user_id) is profile


@pytest.mark.asyncio
async def test_update_profile_creates_missing_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    created_profile = SimpleNamespace(user_id=user_id)
    received_changes: list[dict[str, object]] = []

    class FakeProfileRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_user_id(
            self,
            current_user_id: object,
        ) -> None:
            return None

        async def create(
            self,
            current_user_id: object,
            changes: dict[str, object],
        ) -> object:
            received_changes.append(changes)
            return created_profile

    db = SimpleNamespace(commit=AsyncMock())

    monkeypatch.setattr(
        "app.profiles.services.ProfileRepository",
        FakeProfileRepository,
    )

    result = await update_profile(
        db,
        user_id,
        SimpleNamespace(
            model_dump=lambda **kwargs: {"first_name": "Kate"},
        ),
    )

    assert result is created_profile
    assert received_changes == [{"first_name": "Kate"}]
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_profile_changes_existing_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    profile = SimpleNamespace(
        user_id=user_id,
        first_name="Old name",
    )

    class FakeProfileRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_user_id(
            self,
            current_user_id: object,
        ) -> object:
            return profile

    db = SimpleNamespace(commit=AsyncMock())

    monkeypatch.setattr(
        "app.profiles.services.ProfileRepository",
        FakeProfileRepository,
    )

    result = await update_profile(
        db,
        user_id,
        SimpleNamespace(
            model_dump=lambda **kwargs: {
                "first_name": "Catherine",
            },
        ),
    )

    assert result is profile
    assert profile.first_name == "Catherine"
    db.commit.assert_awaited_once()
