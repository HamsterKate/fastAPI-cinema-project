from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.models import UserProfileModel


class ProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> UserProfileModel | None:
        result = await self.db.execute(
            select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: UUID,
        changes: dict,
    ) -> UserProfileModel:
        profile = UserProfileModel(user_id=user_id, **changes)
        self.db.add(profile)
        await self.db.flush()
        return profile
