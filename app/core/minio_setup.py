import asyncio

from app.core.config import settings
from app.core.storage import get_s3_client


async def ensure_minio_bucket() -> None:
    async with get_s3_client() as s3_client:
        buckets = {
            bucket["Name"] for bucket in (await s3_client.list_buckets())["Buckets"]
        }

        if settings.minio_bucket not in buckets:
            await s3_client.create_bucket(
                Bucket=settings.minio_bucket,
            )
            print(f"Created MinIO bucket: {settings.minio_bucket}")
        else:
            print(f"MinIO bucket already exists: {settings.minio_bucket}")


if __name__ == "__main__":
    asyncio.run(ensure_minio_bucket())
