from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.models import UserProfileModel
from app.profiles.repository import ProfileRepository
from app.profiles.schemas import ProfileUpdateRequestSchema


async def get_profile(
    db: AsyncSession,
    user_id: UUID,
) -> UserProfileModel | None:
    return await ProfileRepository(db).get_by_user_id(user_id)


async def update_profile(
    db: AsyncSession,
    user_id: UUID,
    data: ProfileUpdateRequestSchema,
) -> UserProfileModel:
    repository = ProfileRepository(db)
    profile = await repository.get_by_user_id(user_id)
    changes = data.model_dump(exclude_unset=True)

    if profile is None:
        profile = await repository.create(user_id, changes)
    else:
        for field_name, value in changes.items():
            setattr(profile, field_name, value)

    await db.commit()
    return profile
