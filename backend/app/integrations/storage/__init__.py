from functools import lru_cache

from app.core.config import StorageProvider, settings
from app.integrations.storage.azure_blob import AzureBlobStorage
from app.integrations.storage.base import ObjectStorage
from app.integrations.storage.local import LocalObjectStorage
from app.integrations.storage.minio import MinioObjectStorage
from app.integrations.storage.s3 import S3ObjectStorage


@lru_cache(maxsize=1)
def get_storage() -> ObjectStorage:
    if settings.object_storage_provider is StorageProvider.LOCAL:
        return LocalObjectStorage(settings.local_storage_path)
    if settings.object_storage_provider is StorageProvider.MINIO:
        return MinioObjectStorage()
    if settings.object_storage_provider is StorageProvider.S3:
        return S3ObjectStorage()
    return AzureBlobStorage()


__all__ = ["ObjectStorage", "get_storage"]
