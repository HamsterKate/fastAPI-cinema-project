from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.access_token_expire_minutes
        ),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(
            days=settings.refresh_token_expire_days
        ),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


TokenType = Literal["access", "refresh"]


def decode_token(
    token: str,
    expected_type: TokenType,
) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={
                "require": ["sub", "type", "iat", "exp"],
            },
        )
    except ExpiredSignatureError as exc:
        raise ValueError("Token has expired.") from exc
    except InvalidTokenError as exc:
        raise ValueError("Invalid token.") from exc

    if payload["type"] != expected_type:
        raise ValueError("Invalid token type.")

    if expected_type == "refresh" and not payload.get("jti"):
        raise ValueError("Invalid refresh token.")

    try:
        UUID(payload["sub"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid token subject.") from exc

    return payload
