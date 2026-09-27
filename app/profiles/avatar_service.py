import logging

from uuid import UUID, uuid4

from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.core.storage import get_s3_client


logger = logging.getLogger(__name__)

ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}
MAX_AVATAR_SIZE_BYTES = 1 * 1024 * 1024


async def upload_avatar(
    user_id: UUID,
    avatar: UploadFile,
) -> str:
    extension = ALLOWED_AVATAR_CONTENT_TYPES.get(avatar.content_type)

    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Avatar must be a JPEG or PNG image",
        )

    content = await avatar.read(MAX_AVATAR_SIZE_BYTES + 1)

    if len(content) > MAX_AVATAR_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Avatar size must not exceed 1 MB",
        )

    object_key = f"avatars/{user_id}/{uuid4()}{extension}"

    try:
        async with get_s3_client() as client:
            await client.put_object(
                Bucket=settings.minio_bucket,
                Key=object_key,
                Body=content,
                ContentType=avatar.content_type,
            )
    except ClientError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar",
        ) from error
    finally:
        await avatar.seek(0)

    return object_key


async def delete_avatar(object_key: str) -> None:
    try:
        async with get_s3_client() as client:
            await client.delete_object(
                Bucket=settings.minio_bucket,
                Key=object_key,
            )
    except ClientError:
        logger.exception("Failed to delete avatar: %s", object_key)


async def get_avatar_url(object_key: str | None) -> str | None:
    if object_key is None:
        return None

    async with get_s3_client(settings.minio_public_endpoint) as client:
        return await client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.minio_bucket,
                "Key": object_key,
            },
            ExpiresIn=settings.minio_presigned_url_expire_seconds,
        )
