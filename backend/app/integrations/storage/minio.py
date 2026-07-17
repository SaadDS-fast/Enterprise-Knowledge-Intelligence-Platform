from __future__ import annotations

import asyncio
import io

from minio import Minio

from app.core.config import settings
from app.integrations.storage.base import ObjectStorage


class MinioObjectStorage(ObjectStorage):
    def __init__(self) -> None:
        endpoint = settings.object_storage_endpoint.replace("http://", "").replace("https://", "")
        self.bucket = settings.object_storage_bucket
        self.client = Minio(
            endpoint,
            access_key=settings.object_storage_access_key,
            secret_key=settings.object_storage_secret_key.get_secret_value(),
            secure=settings.object_storage_secure,
        )

    async def _ensure_bucket(self) -> None:
        exists = await asyncio.to_thread(self.client.bucket_exists, self.bucket)
        if not exists:
            await asyncio.to_thread(self.client.make_bucket, self.bucket)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await self._ensure_bucket()
        await asyncio.to_thread(
            self.client.put_object,
            self.bucket,
            key,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )

    async def get(self, key: str) -> bytes:
        response = await asyncio.to_thread(self.client.get_object, self.bucket, key)
        try:
            return await asyncio.to_thread(response.read)
        finally:
            response.close()
            response.release_conn()

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self.client.remove_object, self.bucket, key)

    async def exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(self.client.stat_object, self.bucket, key)
            return True
        except Exception:
            return False
