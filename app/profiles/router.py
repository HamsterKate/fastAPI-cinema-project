from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.models import UserModel, UserProfileModel
from app.db.session import get_db
from app.profiles.schemas import (
    ProfileResponseSchema,
    ProfileUpdateRequestSchema,
)
from app.profiles.avatar_service import (
    delete_avatar,
    get_avatar_url,
    upload_avatar,
)
from app.profiles.services import get_profile, update_profile

router = APIRouter(prefix="/profiles", tags=["profiles"])


async def build_profile_response(
    profile: UserProfileModel,
) -> ProfileResponseSchema:
    response = ProfileResponseSchema.model_validate(profile)
    response.avatar = await get_avatar_url(profile.avatar)

    return response


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
    return await build_profile_response(profile)


@router.patch("/me", response_model=ProfileResponseSchema)
async def update_my_profile_endpoint(
    data: ProfileUpdateRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ProfileResponseSchema:
    profile = await update_profile(db, current_user.id, data)
    return await build_profile_response(profile)


@router.post("/me/avatar", response_model=ProfileResponseSchema)
async def upload_my_avatar_endpoint(
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ProfileResponseSchema:
    profile = await get_profile(db, current_user.id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    previous_avatar_key = profile.avatar
    avatar_key = await upload_avatar(current_user.id, avatar)
    profile.avatar = avatar_key

    try:
        await db.commit()
        await db.refresh(profile)
    except SQLAlchemyError as error:
        await db.rollback()
        await delete_avatar(avatar_key)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save avatar",
        ) from error

    if previous_avatar_key is not None:
        await delete_avatar(previous_avatar_key)

    return await build_profile_response(profile)


@router.delete("/me/avatar", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_avatar_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    profile = await get_profile(db, current_user.id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    avatar_key = profile.avatar

    if avatar_key is None:
        return

    profile.avatar = None

    try:
        await db.commit()
    except SQLAlchemyError as error:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete avatar",
        ) from error

    await delete_avatar(avatar_key)
