from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.models import UserModel
from app.db.session import get_db
from app.profiles.schemas import (
    ProfileResponseSchema,
    ProfileUpdateRequestSchema,
)
from app.profiles.services import get_profile, update_profile


router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get(
    "/me",
    response_model=ProfileResponseSchema,
    responses={404: {"description": "Profile not found"}},
)
async def get_my_profile_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ProfileResponseSchema:
    profile = await get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return ProfileResponseSchema.model_validate(profile)


@router.patch("/me", response_model=ProfileResponseSchema)
async def update_my_profile_endpoint(
    data: ProfileUpdateRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ProfileResponseSchema:
    profile = await update_profile(db, current_user.id, data)
    return ProfileResponseSchema.model_validate(profile)
