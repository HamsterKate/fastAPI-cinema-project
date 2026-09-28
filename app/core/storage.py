from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aioboto3
from aiobotocore.client import AioBaseClient
from botocore.config import Config

from app.core.config import settings


_session = aioboto3.Session()


@asynccontextmanager
async def get_s3_client(
    endpoint_url: str | None = None,
) -> AsyncIterator[AioBaseClient]:
    async with _session.client(
        service_name="s3",
        endpoint_url=endpoint_url or settings.minio_endpoint,
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    ) as client:
        yield client
