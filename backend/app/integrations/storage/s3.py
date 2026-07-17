from app.integrations.storage.base import ObjectStorage


class S3ObjectStorage(ObjectStorage):
    def _unavailable(self) -> RuntimeError:
        return RuntimeError(
            "Install/configure an S3 adapter before selecting OBJECT_STORAGE_PROVIDER=s3"
        )

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        raise self._unavailable()

    async def get(self, key: str) -> bytes:
        raise self._unavailable()

    async def delete(self, key: str) -> None:
        raise self._unavailable()

    async def exists(self, key: str) -> bool:
        raise self._unavailable()
