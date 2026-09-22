from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.models import (
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)
from app.accounts.schemas import UserRegistrationSchema
from app.accounts.security import hash_password


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
    await db.commit()
    await db.refresh(user)

    return user
