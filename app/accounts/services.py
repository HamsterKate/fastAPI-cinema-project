from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.email import send_activation_email
from app.accounts.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.accounts.models import (
    ActivationTokenModel,
    RefreshTokenModel,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)
from app.accounts.schemas import (
    TokenResponseSchema,
    UserLoginSchema,
    UserRegistrationSchema,
)
from app.accounts.security import hash_password, verify_password
from app.accounts.tokens import generate_token, hash_token

from app.core.config import settings


async def create_activation_token(
        db: AsyncSession,
        user: UserModel,
) -> str:
    token = generate_token()

    activation_token = ActivationTokenModel(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=(
                datetime.now(timezone.utc)
                + timedelta(minutes=settings.activation_token_expire_minutes)
        ),
    )

    db.add(activation_token)
    await db.flush()

    return token


async def register_user(
        db: AsyncSession,
        user_data: UserRegistrationSchema,
) -> UserModel:
    result = await db.execute(
        select(UserModel).where(UserModel.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise ValueError("User with this email already exists.")

    result = await db.execute(
        select(UserGroupModel).where(
            UserGroupModel.name == UserGroupEnum.USER
        )
    )
    user_group = result.scalar_one_or_none()

    if user_group is None:
        raise ValueError("Default user group does not exist.")

    user = UserModel(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        is_active=False,
        is_verified=False,
        group_id=user_group.id,
    )

    db.add(user)
    await db.flush()

    activation_token = await create_activation_token(db, user)

    await db.commit()
    await db.refresh(user)

    await send_activation_email(
        recipient=user.email,
        token=activation_token,
    )

    return user


async def activate_user(
        db: AsyncSession,
        token: str,
) -> UserModel:
    token_hash = hash_token(token)

    result = await db.execute(
        select(ActivationTokenModel).where(
            ActivationTokenModel.token_hash == token_hash
        )
    )
    activation = result.scalar_one_or_none()

    if activation is None:
        raise ValueError("Invalid activation token.")

    if activation.expires_at <= datetime.now(timezone.utc):
        raise ValueError("Activation token has expired.")

    result = await db.execute(
        select(UserModel).where(
            UserModel.id == activation.user_id
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise ValueError("User not found.")

    user.is_active = True
    user.is_verified = True

    await db.delete(activation)
    await db.commit()
    await db.refresh(user)

    return user


async def resend_activation(
        db: AsyncSession,
        email: str,
) -> None:
    result = await db.execute(
        select(UserModel).where(UserModel.email == email)
    )
    user = result.scalar_one_or_none()

    if user is None or user.is_active:
        return

    result = await db.execute(
        select(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user.id
        )
    )
    existing_token = result.scalar_one_or_none()

    if existing_token:
        await db.delete(existing_token)
        await db.flush()

    token = await create_activation_token(db, user)

    await db.commit()

    await send_activation_email(
        recipient=user.email,
        token=token,
    )


async def login_user(
        db: AsyncSession,
        user_data: UserLoginSchema,
) -> TokenResponseSchema:
    result = await db.execute(
        select(UserModel).where(UserModel.email == user_data.email)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(
        user_data.password,
        user.hashed_password,
    ):
        raise ValueError("Invalid email or password.")

    if not user.is_active or not user.is_verified:
        raise ValueError("Account is not activated.")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    refresh_payload = decode_token(
        refresh_token,
        expected_type="refresh",
    )

    refresh_token_record = RefreshTokenModel(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.fromtimestamp(
            refresh_payload["exp"],
            tz=timezone.utc,
        ),
    )

    db.add(refresh_token_record)
    await db.commit()

    return TokenResponseSchema(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def revoke_token_chain(
        db: AsyncSession,
        token: RefreshTokenModel,
) -> None:
    revoked_at = datetime.now(timezone.utc)
    current_token = token

    while current_token is not None:
        if current_token.revoked_at is None:
            current_token.revoked_at = revoked_at

        if current_token.replaced_by_token_id is None:
            break

        result = await db.execute(
            select(RefreshTokenModel)
            .where(
                RefreshTokenModel.id
                == current_token.replaced_by_token_id,
                RefreshTokenModel.user_id == token.user_id,
            )
            .with_for_update()
        )

        current_token = result.scalar_one_or_none()

async def refresh_user_tokens(
    db: AsyncSession,
    refresh_token: str,
) -> TokenResponseSchema:
    payload = decode_token(
        refresh_token,
        expected_type="refresh",
    )

    user_id = UUID(payload["sub"])

    result = await db.execute(
        select(RefreshTokenModel)
        .where(
            RefreshTokenModel.token_hash == hash_token(refresh_token),
            RefreshTokenModel.user_id == user_id,
        )
        .with_for_update()
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        raise ValueError("Invalid refresh token.")

    # A revoked token used again indicates possible token theft.
    if stored_token.revoked_at is not None:
        if stored_token.replaced_by_token_id is not None:
            await revoke_token_chain(db, stored_token)
            await db.commit()

        raise ValueError("Refresh token has been revoked.")

    if stored_token.expires_at <= datetime.now(timezone.utc):
        raise ValueError("Refresh token has expired.")

    result = await db.execute(
        select(UserModel).where(
            UserModel.id == user_id,
        )
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active or not user.is_verified:
        raise ValueError("Account is not active.")

    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    new_payload = decode_token(
        new_refresh_token,
        expected_type="refresh",
    )

    new_token_record = RefreshTokenModel(
        user_id=user.id,
        token_hash=hash_token(new_refresh_token),
        expires_at=datetime.fromtimestamp(
            new_payload["exp"],
            tz=timezone.utc,
        ),
    )

    db.add(new_token_record)
    await db.flush()

    stored_token.revoked_at = datetime.now(timezone.utc)
    stored_token.replaced_by_token_id = new_token_record.id

    await db.commit()

    return TokenResponseSchema(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


async def logout_user(
    db: AsyncSession,
    refresh_token: str,
) -> None:
    payload = decode_token(refresh_token, expected_type="refresh")

    result = await db.execute(
        select(RefreshTokenModel)
        .where(
            RefreshTokenModel.token_hash == hash_token(refresh_token),
            RefreshTokenModel.user_id == UUID(payload["sub"]),
        )
        .with_for_update()
    )

    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        raise ValueError("Invalid refresh token.")

    if stored_token.revoked_at is not None:
        raise ValueError("Refresh token has been revoked.")

    stored_token.revoked_at = datetime.now(timezone.utc)
    await db.commit()
