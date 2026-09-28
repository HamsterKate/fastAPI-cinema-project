from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from types import SimpleNamespace

import pytest

from app.accounts.services import (
    activate_user,
    create_activation_token,
    login_user,
    logout_user,
    forgot_password,
    resend_activation,
    reset_password,
)
from app.accounts.schemas import UserLoginSchema


class FakeScalarResult:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value


@pytest.mark.asyncio
async def test_activate_user_rejects_unknown_token() -> None:
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=FakeScalarResult(None),
        ),
    )

    with pytest.raises(
        ValueError,
        match="Invalid activation token",
    ):
        await activate_user(db, "unknown-token")

    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_resend_activation_ignores_unknown_email() -> None:
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=FakeScalarResult(None),
        ),
    )

    await resend_activation(db, "missing@example.com")

    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_forgot_password_ignores_inactive_user() -> None:
    inactive_user = SimpleNamespace(
        is_active=False,
        is_verified=False,
    )
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=FakeScalarResult(inactive_user),
        ),
    )

    await forgot_password(db, "inactive@example.com")

    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_activate_user_rejects_expired_token() -> None:
    expired_activation = SimpleNamespace(
        expires_at=datetime.now(timezone.utc)
        - timedelta(minutes=1),
    )
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=FakeScalarResult(expired_activation),
        ),
    )

    with pytest.raises(
        ValueError,
        match="Activation token has expired",
    ):
        await activate_user(db, "expired-token")


@pytest.mark.asyncio
async def test_activate_user_rejects_token_without_user() -> None:
    activation = SimpleNamespace(
        user_id=uuid4(),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=1),
    )
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                FakeScalarResult(activation),
                FakeScalarResult(None),
            ],
        ),
    )

    with pytest.raises(
        ValueError,
        match="User not found",
    ):
        await activate_user(db, "valid-token-without-user")


@pytest.mark.asyncio
async def test_reset_password_rejects_unknown_token() -> None:
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=FakeScalarResult(None),
        ),
    )

    with pytest.raises(
        ValueError,
        match="Invalid or expired password reset token",
    ):
        await reset_password(
            db,
            "unknown-token",
            "NewStrongPassword1!",
        )


@pytest.mark.asyncio
async def test_create_activation_token_stores_hashed_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(id=uuid4())
    db = SimpleNamespace(
        add=Mock(),
        flush=AsyncMock(),
    )

    monkeypatch.setattr(
        "app.accounts.services.generate_token",
        lambda: "plain-token",
    )
    monkeypatch.setattr(
        "app.accounts.services.hash_token",
        lambda token: f"hashed-{token}",
    )

    token = await create_activation_token(db, user)

    assert token == "plain-token"
    db.flush.assert_awaited_once()

    stored_token = db.add.call_args.args[0]
    assert stored_token.user_id == user.id
    assert stored_token.token_hash == "hashed-plain-token"
    assert stored_token.expires_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_login_user_rejects_unknown_email() -> None:
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=FakeScalarResult(None),
        ),
    )

    with pytest.raises(
        ValueError,
        match="Invalid email or password",
    ):
        await login_user(
            db,
            UserLoginSchema(
                email="missing@example.com",
                password="StrongPassword1!",
            ),
        )


@pytest.mark.asyncio
async def test_logout_user_rejects_unknown_refresh_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=FakeScalarResult(None),
        ),
    )

    monkeypatch.setattr(
        "app.accounts.services.decode_token",
        lambda token, expected_type: {"sub": str(user_id)},
    )

    with pytest.raises(
        ValueError,
        match="Invalid refresh token",
    ):
        await logout_user(db, "unknown-refresh-token")


@pytest.mark.asyncio
async def test_login_user_creates_and_stores_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        hashed_password="hashed-password",
        is_active=True,
        is_verified=True,
    )
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=FakeScalarResult(user),
        ),
        add=Mock(),
        commit=AsyncMock(),
    )
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    monkeypatch.setattr(
        "app.accounts.services.verify_password",
        lambda password, hashed_password: True,
    )
    monkeypatch.setattr(
        "app.accounts.services.create_access_token",
        lambda user_id: "access-token",
    )
    monkeypatch.setattr(
        "app.accounts.services.create_refresh_token",
        lambda user_id: "refresh-token",
    )
    monkeypatch.setattr(
        "app.accounts.services.decode_token",
        lambda token, expected_type: {
            "exp": int(expires_at.timestamp()),
        },
    )
    monkeypatch.setattr(
        "app.accounts.services.hash_token",
        lambda token: f"hashed-{token}",
    )

    tokens = await login_user(
        db,
        UserLoginSchema(
            email="user@example.com",
            password="StrongPassword1!",
        ),
    )

    assert tokens.access_token == "access-token"
    assert tokens.refresh_token == "refresh-token"
    db.commit.assert_awaited_once()

    stored_token = db.add.call_args.args[0]
    assert stored_token.user_id == user.id
    assert stored_token.token_hash == "hashed-refresh-token"


@pytest.mark.asyncio
async def test_login_user_rejects_inactive_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        hashed_password="hashed-password",
        is_active=False,
        is_verified=False,
    )
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=FakeScalarResult(user),
        ),
    )

    monkeypatch.setattr(
        "app.accounts.services.verify_password",
        lambda password, hashed_password: True,
    )

    with pytest.raises(
        ValueError,
        match="Account is not activated",
    ):
        await login_user(
            db,
            UserLoginSchema(
                email="inactive@example.com",
                password="StrongPassword1!",
            ),
        )


@pytest.mark.asyncio
async def test_logout_user_rejects_revoked_refresh_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    stored_token = SimpleNamespace(
        revoked_at=datetime.now(timezone.utc),
    )
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=FakeScalarResult(stored_token),
        ),
    )

    monkeypatch.setattr(
        "app.accounts.services.decode_token",
        lambda token, expected_type: {"sub": str(user_id)},
    )

    with pytest.raises(
        ValueError,
        match="Refresh token has been revoked",
    ):
        await logout_user(db, "revoked-refresh-token")
